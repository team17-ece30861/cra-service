"""Contract 0.3.0 (plan task 5.9): Q7, Q9 and "a 422 lists every problem".

Team 17's own checks, kept out of acceptance/ (the portable cross-team suite). Every call
goes through acceptance.client.Service, so each response is also checked against
openapi.yaml.
"""

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from acceptance.client import Contract, Service
from acceptance.draft_cases import FIELDS, FIXED, create_reportable, read_draft
from acceptance.submission_cases import audit_log, submit_report
from core.models import AuditEntry, ReportSubmission, Ticket
from tests.test_phase3_api import DjangoTransport

FUTURE_FIX = [{"field": "fix.available_at", "message": "must not be later than now"}]
TICKET = {
    "source": "external_researcher",
    "title": "Authentication bypass",
    "description": "Simulated vulnerability.",
    "product": {"manufacturer": "Acme", "name": "Router OS", "affected_versions": ["4.1.0"]},
}


@pytest.fixture
def service():
    service = Service(DjangoTransport())
    service.expect("POST", "/test/reset", 204, actor=None)
    service.fix_clock(FIXED)
    return service


def post_ticket(service, body, status, **kwargs):
    return service.expect("POST", "/tickets", status, body=body, **kwargs)


def patch_ticket(service, ticket_id, body, status):
    return service.expect(
        "PATCH", f"/tickets/{ticket_id}", status, template="/tickets/{id}", body=body
    )


def assert_nothing_stored():
    assert Ticket.objects.count() == 0
    assert AuditEntry.objects.count() == 0


# --- Q7: submit rejects a fix time later than now ---


@pytest.mark.django_db(transaction=True)
class TestSubmitFutureFixTime:
    @pytest.mark.parametrize(
        "available_at",
        ["2026-10-05T09:00:01Z", "2026-10-05T11:00:01+02:00", "2030-01-01T00:00:00Z"],
    )
    def test_later_than_now_is_422_and_stores_nothing(self, service, available_at):
        problem = post_ticket(service, {**TICKET, "fix": {"available_at": available_at}}, 422)
        assert problem["title"] == "Rule violation"
        assert problem["errors"] == FUTURE_FIX
        assert_nothing_stored()

    def test_fix_object_without_a_time_is_not_checked(self, service):
        ticket = post_ticket(service, {**TICKET, "fix": {"description": "Patch"}}, 201)
        assert ticket["fix"] == {"description": "Patch", "fixed_versions": []}

    @pytest.mark.parametrize(
        "available_at",
        [
            FIXED,
            "2026-10-05T11:00:00+02:00",  # the same instant with an offset
            "2026-10-05T09:00:00.999Z",  # truncated to the second (AC-14), so equal to now
            "2026-10-05T08:59:59Z",
        ],
    )
    def test_equal_to_or_before_now_is_accepted(self, service, available_at):
        ticket = post_ticket(service, {**TICKET, "fix": {"available_at": available_at}}, 201)
        assert ticket["fix"]["available_at"] <= FIXED
        stored = service.get(ticket["id"])
        assert stored["fix"]["available_at"] == ticket["fix"]["available_at"]
        assert [entry["action"] for entry in audit_log(service, ticket["id"])] == ["created"]

    def test_moving_the_clock_changes_the_verdict(self, service):
        body = {**TICKET, "fix": {"available_at": "2026-10-06T00:00:00Z"}}
        post_ticket(service, body, 422)
        service.fix_clock("2026-10-06T00:00:00Z")
        post_ticket(service, body, 201)

    @pytest.mark.parametrize(
        "change",
        [
            {"title": ""},
            {"state": "reportable"},
            {"member_states": ["XX"]},
        ],
        ids=["bad-field", "system-field", "bad-member-state"],
    )
    def test_schema_errors_win_over_the_future_fix_time(self, service, change):
        body = {**TICKET, **change, "fix": {"available_at": "2030-01-01T00:00:00Z"}}
        problem = post_ticket(service, body, 400)
        assert "fix.available_at" not in {error["field"] for error in problem["errors"]}
        assert_nothing_stored()

    def test_missing_actor_wins_over_the_future_fix_time(self, service):
        body = {**TICKET, "fix": {"available_at": "2030-01-01T00:00:00Z"}}
        problem = post_ticket(service, body, 400, actor=None)
        assert [error["field"] for error in problem["errors"]] == ["X-Actor"]
        assert_nothing_stored()


# --- Q9: member_states may be exactly ["unknown"] ---


@pytest.mark.django_db(transaction=True)
class TestUnknownMemberStates:
    def test_submit_accepts_and_echoes_unknown(self, service):
        ticket = post_ticket(service, {**TICKET, "member_states": ["unknown"]}, 201)
        assert ticket["member_states"] == ["unknown"]
        assert service.get(ticket["id"])["member_states"] == ["unknown"]
        listed = service.expect("GET", "/tickets", 200)
        assert [row["member_states"] for row in listed] == [["unknown"]]
        (created,) = audit_log(service, ticket["id"])
        assert {"field": "member_states", "old": None, "new": ["unknown"]} in created["changes"]

    @pytest.mark.parametrize(
        "member_states",
        [
            ["DE", "unknown"],
            ["unknown", "DE"],
            ["unknown", "unknown"],
        ],
    )
    def test_unknown_mixed_or_repeated_is_400_on_member_states(self, service, member_states):
        problem = post_ticket(service, {**TICKET, "member_states": member_states}, 400)
        assert [error["field"] for error in problem["errors"]] == ["member_states"]
        assert_nothing_stored()

    @pytest.mark.parametrize(
        "member_states", [["UNKNOWN"], ["Unknown"], [" unknown"], ["unknown "], "unknown", [None]]
    )
    def test_only_the_exact_literal_is_accepted(self, service, member_states):
        post_ticket(service, {**TICKET, "member_states": member_states}, 400)
        assert_nothing_stored()

    def test_update_to_unknown_and_back(self, service):
        ticket = post_ticket(service, {**TICKET, "member_states": ["DE"]}, 201)
        updated = patch_ticket(service, ticket["id"], {"member_states": ["unknown"]}, 200)
        assert updated["member_states"] == ["unknown"]
        entry = audit_log(service, ticket["id"])[-1]
        assert entry["action"] == "updated"
        assert entry["changes"] == [{"field": "member_states", "old": ["DE"], "new": ["unknown"]}]
        updated = patch_ticket(service, ticket["id"], {"member_states": ["NL"]}, 200)
        assert updated["member_states"] == ["NL"]
        assert AuditEntry.objects.count() == 3

    def test_update_with_unknown_mixed_changes_nothing(self, service):
        ticket = post_ticket(service, {**TICKET, "member_states": ["DE"]}, 201)
        before = service.get(ticket["id"])
        problem = patch_ticket(
            service,
            ticket["id"],
            {"title": "Must not persist", "member_states": ["unknown", "FR"]},
            400,
        )
        assert [error["field"] for error in problem["errors"]] == ["member_states"]
        assert service.get(ticket["id"]) == before
        assert AuditEntry.objects.count() == 1

    def test_unknown_versions_are_free_text(self, service):
        product = {**TICKET["product"], "affected_versions": ["unknown"]}
        ticket = post_ticket(service, {**TICKET, "product": product}, 201)
        assert ticket["product"]["affected_versions"] == ["unknown"]


@pytest.mark.django_db(transaction=True)
class TestUnknownMemberStatesInReports:
    def test_early_warning_draft_counts_unknown_as_filled_in(self, service):
        ticket_id = create_reportable(service, product=TICKET["product"], member_states=["unknown"])
        draft = read_draft(service, ticket_id, "early_warning")
        assert draft["missing_fields"] == []
        assert draft["content"]["member_states"] == ["unknown"]

    def test_empty_member_states_are_still_missing(self, service):
        ticket_id = create_reportable(service, product=TICKET["product"], member_states=[])
        assert read_draft(service, ticket_id, "early_warning")["missing_fields"] == [
            "member_states"
        ]
        submit_report(service, ticket_id, "early_warning", 422)

    def test_unknown_versions_and_member_states_record_an_early_warning(self, service):
        product = {**TICKET["product"], "affected_versions": ["unknown"]}
        ticket_id = create_reportable(service, product=product, member_states=["unknown"])
        recorded = submit_report(service, ticket_id, "early_warning")
        assert recorded["status"] == "submitted"
        assert recorded["content"]["member_states"] == ["unknown"]
        assert recorded["content"]["product"]["affected_versions"] == ["unknown"]
        stored = ReportSubmission.objects.get(ticket_id=ticket_id, report_type="early_warning")
        assert stored.content["member_states"] == ["unknown"]
        entry = audit_log(service, ticket_id)[-1]
        assert entry["action"] == "report_submitted"
        assert entry["changes"][0]["new"]["content"]["member_states"] == ["unknown"]

    def test_unknown_is_a_value_for_the_later_reports_too(self, service):
        fields = deepcopy(FIELDS)
        fields["member_states"] = ["unknown"]
        ticket_id = create_reportable(service, **fields)
        for report_type in ("notification", "final_report"):
            draft = read_draft(service, ticket_id, report_type)
            assert draft["missing_fields"] == []
            assert draft["content"]["member_states"] == ["unknown"]


# --- A 422 lists every rule problem found ---


@pytest.mark.django_db(transaction=True)
def test_update_422_lists_every_rule_problem(service):
    ticket_id = create_reportable(service, product=TICKET["product"])
    problem = patch_ticket(
        service,
        ticket_id,
        {"aware_at": "2026-10-05T09:00:01Z", "fix": {"available_at": "2026-10-05T09:00:01Z"}},
        422,
    )
    assert sorted(error["field"] for error in problem["errors"]) == [
        "aware_at",
        "change_reason",
        "fix.available_at",
    ]
    assert AuditEntry.objects.count() == 2


# --- The contract says the same as the code ---

TICKET_CREATE = Draft202012Validator(
    {"$ref": "urn:cra-contract#/components/schemas/TicketCreate"}, registry=Contract().registry
)
TICKET_UPDATE = Draft202012Validator(
    {"$ref": "urn:cra-contract#/components/schemas/TicketUpdate"}, registry=Contract().registry
)


@pytest.mark.parametrize(
    "member_states,valid",
    [
        (["unknown"], True),
        (["DE", "NL"], True),
        ([], True),
        (["DE", "unknown"], False),
        (["unknown", "unknown"], False),
        (["UNKNOWN"], False),
        ("unknown", False),
    ],
)
def test_contract_member_states_match_the_code(member_states, valid):
    assert TICKET_CREATE.is_valid({**TICKET, "member_states": member_states}) is valid
    assert TICKET_UPDATE.is_valid({"member_states": member_states}) is valid


def test_contract_lists_422_for_submit_and_version_030():
    document = Contract().document
    assert document["info"]["version"] == "0.3.0"
    assert "422" in document["paths"]["/tickets"]["post"]["responses"]
