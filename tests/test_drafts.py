import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone

import pytest

from core.domain.drafts import DraftResult, build_draft

TICKET_ID = "4e545f3e-fde2-4878-b8ce-47553009f4a6"
AWARE_AT = datetime(2026, 10, 5, 9, tzinfo=UTC)
PRIVATE_REPORTER = "private-reporter@example.invalid"
PRODUCT = {
    "manufacturer": "Acme",
    "name": "Router",
    "affected_versions": ["1.0", "1.1"],
}
TICKET_FIELDS = {
    "source": "external_researcher",
    "title": "Intake title",
    "description": "Intake description is not the vulnerability description.",
    "product": PRODUCT,
    "member_states": ["DE", "FR"],
    "vulnerability": {"cve_id": "CVE-2026-12345", "description": "Authentication bypass"},
    "exploit": {"description": "Observed exploitation"},
    "mitigations": {"taken": "Disabled the endpoint", "for_users": "Install version 1.2"},
    "sensitivity": "AMBER",
    "severity": "high",
    "impact": "Unauthorized access",
    "malicious_actor": "Unknown actor",
    "fix": {
        "available_at": "2026-10-06T10:00:00Z",
        "description": "Corrected authentication",
        "fixed_versions": ["1.2"],
    },
    "reporter": {"name": PRIVATE_REPORTER, "contact": PRIVATE_REPORTER},
}
REQUIRED_FIELDS = {
    "early_warning": [
        "product.manufacturer",
        "product.name",
        "product.affected_versions",
        "member_states",
    ],
    "notification": [
        "product.manufacturer",
        "product.name",
        "product.affected_versions",
        "member_states",
        "vulnerability.description",
        "exploit.description",
        "mitigations.taken",
        "mitigations.for_users",
        "sensitivity",
    ],
    "final_report": [
        "product.manufacturer",
        "product.name",
        "product.affected_versions",
        "member_states",
        "vulnerability.description",
        "exploit.description",
        "mitigations.taken",
        "mitigations.for_users",
        "sensitivity",
        "severity",
        "impact",
        "fix.available_at",
        "fix.description",
        "fix.fixed_versions",
    ],
    "user_advisory": [
        "product.manufacturer",
        "product.name",
        "product.affected_versions",
        "vulnerability.description",
        "mitigations.for_users",
    ],
}
EXPECTED_CONTENT = {
    "early_warning": {"product": PRODUCT, "member_states": ["DE", "FR"]},
    "notification": {
        "product": PRODUCT,
        "member_states": ["DE", "FR"],
        "vulnerability": {"cve_id": "CVE-2026-12345", "description": "Authentication bypass"},
        "exploit": {"description": "Observed exploitation"},
        "mitigations": {"taken": "Disabled the endpoint", "for_users": "Install version 1.2"},
        "sensitivity": "AMBER",
    },
    "final_report": {
        "product": PRODUCT,
        "member_states": ["DE", "FR"],
        "vulnerability": {"cve_id": "CVE-2026-12345", "description": "Authentication bypass"},
        "exploit": {"description": "Observed exploitation"},
        "mitigations": {"taken": "Disabled the endpoint", "for_users": "Install version 1.2"},
        "sensitivity": "AMBER",
        "severity": "high",
        "impact": "Unauthorized access",
        "malicious_actor": "Unknown actor",
        "fix": {
            "available_at": "2026-10-06T10:00:00Z",
            "description": "Corrected authentication",
            "fixed_versions": ["1.2"],
        },
    },
    "user_advisory": {
        "product": PRODUCT,
        "vulnerability": {"cve_id": "CVE-2026-12345", "description": "Authentication bypass"},
        "mitigations": {"for_users": "Install version 1.2"},
        "severity": "high",
        "impact": "Unauthorized access",
        "fix": {
            "available_at": "2026-10-06T10:00:00Z",
            "description": "Corrected authentication",
            "fixed_versions": ["1.2"],
        },
    },
}
REQUIRED_CASES = [
    (report_type, field) for report_type, fields in REQUIRED_FIELDS.items() for field in fields
]


def _build(report_type, fields, *, aware_at=AWARE_AT):
    return build_draft(
        report_type=report_type,
        ticket_id=TICKET_ID,
        aware_at=aware_at,
        ticket_fields=fields,
    )


@pytest.mark.parametrize("report_type", REQUIRED_FIELDS)
def test_complete_draft_matches_model_c_exactly(report_type):
    expected = {
        "ticket_id": TICKET_ID,
        "aware_at": "2026-10-05T09:00:00Z",
        **EXPECTED_CONTENT[report_type],
    }

    assert _build(report_type, deepcopy(TICKET_FIELDS)) == DraftResult(expected, [])


@pytest.mark.parametrize("report_type", REQUIRED_FIELDS)
def test_empty_ticket_lists_exact_required_fields(report_type):
    result = _build(report_type, {})

    assert result.missing_fields == REQUIRED_FIELDS[report_type]
    assert result.content == {"ticket_id": TICKET_ID, "aware_at": "2026-10-05T09:00:00Z"}


@pytest.mark.parametrize(("report_type", "field"), REQUIRED_CASES)
def test_each_required_field_is_reported_when_absent(report_type, field):
    fields = deepcopy(TICKET_FIELDS)
    if "." in field:
        parent, name = field.split(".")
        del fields[parent][name]
    else:
        del fields[field]

    assert _build(report_type, fields).missing_fields == [field]


@pytest.mark.parametrize(("report_type", "field"), REQUIRED_CASES)
@pytest.mark.parametrize("empty_value", [None, "", []], ids=["null", "empty-string", "empty-list"])
def test_empty_required_values_remain_missing(report_type, field, empty_value):
    fields = deepcopy(TICKET_FIELDS)
    if "." in field:
        parent, name = field.split(".")
        fields[parent][name] = empty_value
    else:
        fields[field] = empty_value

    assert _build(report_type, fields).missing_fields == [field]


@pytest.mark.parametrize("report_type", REQUIRED_FIELDS)
def test_model_c_fields_can_be_completed_one_at_a_time(report_type):
    fields = {}
    required_fields = REQUIRED_FIELDS[report_type]

    for position, field in enumerate(required_fields):
        if "." in field:
            parent, name = field.split(".")
            fields.setdefault(parent, {})[name] = deepcopy(TICKET_FIELDS[parent][name])
        else:
            fields[field] = deepcopy(TICKET_FIELDS[field])

        assert _build(report_type, fields).missing_fields == required_fields[position + 1 :]


@pytest.mark.parametrize("report_type", REQUIRED_FIELDS)
@pytest.mark.parametrize("section", ["product", "vulnerability", "exploit", "mitigations", "fix"])
def test_cleared_nested_sections_are_treated_as_missing(report_type, section):
    fields = deepcopy(TICKET_FIELDS)
    fields[section] = None
    expected = [field for field in REQUIRED_FIELDS[report_type] if field.startswith(f"{section}.")]

    assert _build(report_type, fields).missing_fields == expected


@pytest.mark.parametrize("report_type", REQUIRED_FIELDS)
def test_reporter_and_unlisted_nested_fields_never_enter_drafts(report_type):
    fields = deepcopy(TICKET_FIELDS)
    for section in ("product", "vulnerability", "exploit", "mitigations", "fix"):
        fields[section]["reporter"] = {"contact": PRIVATE_REPORTER}
        fields[section]["unlisted"] = PRIVATE_REPORTER
    fields["ticket_id"] = PRIVATE_REPORTER
    fields["aware_at"] = PRIVATE_REPORTER

    result = _build(report_type, fields)

    assert PRIVATE_REPORTER not in json.dumps(result.content)
    assert result.missing_fields == []
    assert result.content["ticket_id"] == TICKET_ID
    assert result.content["aware_at"] == "2026-10-05T09:00:00Z"


@pytest.mark.parametrize("report_type", REQUIRED_FIELDS)
def test_optional_fields_are_not_required_when_absent(report_type):
    fields = deepcopy(TICKET_FIELDS)
    del fields["vulnerability"]["cve_id"]
    del fields["malicious_actor"]
    if report_type == "user_advisory":
        del fields["severity"]
        del fields["impact"]
        del fields["fix"]

    result = _build(report_type, fields)

    assert result.missing_fields == []
    assert "cve_id" not in result.content.get("vulnerability", {})
    assert "malicious_actor" not in result.content
    if report_type == "user_advisory":
        assert "fix" not in result.content
        assert "severity" not in result.content
        assert "impact" not in result.content


@pytest.mark.parametrize("report_type", REQUIRED_FIELDS)
def test_building_and_mutating_drafts_does_not_change_ticket_or_other_drafts(report_type):
    fields = deepcopy(TICKET_FIELDS)
    before = deepcopy(fields)
    result = _build(report_type, fields)
    other = _build(report_type, fields)

    assert fields == before
    result.content["product"]["affected_versions"].append("output-only")
    result.content["product"]["name"] = "Changed output"
    result.missing_fields.append("output-only")

    assert fields == before
    assert other.content["product"] == PRODUCT
    assert other.missing_fields == []
    fields["product"]["affected_versions"].append("input-only")
    assert "input-only" not in result.content["product"]["affected_versions"]
    assert "input-only" not in other.content["product"]["affected_versions"]


def test_awareness_is_normalized_to_utc_seconds():
    local_awareness = datetime(2026, 10, 5, 11, 0, 0, 999999, tzinfo=timezone(timedelta(hours=2)))

    assert _build("early_warning", {}, aware_at=local_awareness).content["aware_at"] == (
        "2026-10-05T09:00:00Z"
    )


@pytest.mark.parametrize("report_type", ["final_report", "user_advisory"])
@pytest.mark.parametrize(
    "fix_time",
    [
        "2026-10-06T12:00:00.987+02:00",
        datetime(2026, 10, 6, 12, 0, 0, 987000, tzinfo=timezone(timedelta(hours=2))),
    ],
    ids=["timestamp", "datetime"],
)
def test_fix_availability_is_normalized_to_utc_seconds(report_type, fix_time):
    fields = deepcopy(TICKET_FIELDS)
    fields["fix"]["available_at"] = fix_time

    assert _build(report_type, fields).content["fix"]["available_at"] == "2026-10-06T10:00:00Z"


def test_naive_awareness_is_rejected_at_the_domain_boundary():
    with pytest.raises(ValueError, match="timezone-aware"):
        _build("early_warning", {}, aware_at=AWARE_AT.replace(tzinfo=None))


@pytest.mark.parametrize("report_type", ["final_report", "user_advisory"])
def test_naive_fix_availability_is_rejected_at_the_domain_boundary(report_type):
    fields = deepcopy(TICKET_FIELDS)
    fields["fix"]["available_at"] = datetime(2026, 10, 6, 10)

    with pytest.raises(ValueError, match="timezone-aware"):
        _build(report_type, fields)


def test_unknown_report_type_is_rejected_without_mutating_inputs():
    fields = deepcopy(TICKET_FIELDS)
    before = deepcopy(fields)

    with pytest.raises(ValueError, match="unknown report type"):
        _build("unknown", fields)

    assert fields == before
