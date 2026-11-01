"""4.D5 listing helpers; expected values worked out by hand from REQ-10 and Q2."""

from datetime import UTC, datetime, timedelta, timezone

from core.domain.listing import next_due_at, urgency_key

T = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)
DUE = {"early_warning": T, "notification": T + timedelta(days=2), "final_report": None}


def test_next_due_is_the_earliest_unrecorded_deadline():
    assert next_due_at(applicable=True, due_times=DUE, submitted=set()) == T


def test_recorded_reports_no_longer_count():
    assert next_due_at(applicable=True, due_times=DUE, submitted={"early_warning"}) == (
        T + timedelta(days=2)
    )


def test_a_final_report_waiting_for_a_fix_has_no_deadline():
    submitted = {"early_warning", "notification"}
    assert next_due_at(applicable=True, due_times=DUE, submitted=submitted) is None


def test_final_report_deadline_counts_once_set():
    due = {**DUE, "final_report": T + timedelta(days=14)}
    submitted = {"early_warning", "notification"}
    assert next_due_at(applicable=True, due_times=due, submitted=submitted) == T + timedelta(
        days=14
    )


def test_not_applicable_tickets_have_no_next_deadline():
    assert next_due_at(applicable=False, due_times=DUE, submitted=set()) is None


def test_all_recorded_means_no_next_deadline():
    due = {**DUE, "final_report": T + timedelta(days=14)}
    submitted = {"early_warning", "notification", "final_report"}
    assert next_due_at(applicable=True, due_times=due, submitted=submitted) is None


def test_next_due_is_utc_to_the_second():
    eastern = timezone(timedelta(hours=-5))
    due = {"early_warning": datetime(2026, 10, 5, 4, 0, 0, 900_000, tzinfo=eastern)}
    assert next_due_at(applicable=True, due_times=due, submitted=set()) == T


def key(due, received, ticket_id):
    return urgency_key(next_due_at=due, received_at=received, ticket_id=ticket_id)


def test_nearest_deadline_first_and_no_deadline_last():
    rows = [
        key(None, T - timedelta(days=9), "a"),
        key(T + timedelta(hours=1), T, "b"),
        key(T, T, "c"),
    ]
    assert [row[-1] for row in sorted(rows)] == ["c", "b", "a"]


def test_equal_deadlines_go_to_the_ticket_received_first_then_id():
    rows = [
        key(T, T, "b"),
        key(T, T - timedelta(seconds=1), "z"),
        key(T, T, "a"),
    ]
    assert [row[-1] for row in sorted(rows)] == ["z", "a", "b"]


def test_tickets_without_deadlines_go_oldest_first_then_id():
    rows = [key(None, T, "b"), key(None, T, "a"), key(None, T - timedelta(hours=1), "c")]
    assert [row[-1] for row in sorted(rows)] == ["c", "a", "b"]
