import json

import pytest

from acceptance.client import Contract, Response


@pytest.mark.parametrize("now", [123, "2026-10-05T09:00:00"], ids=["wrong-type", "missing-offset"])
def test_contract_validator_rejects_invalid_clock_responses(now):
    response = Response(200, "application/json", json.dumps({"now": now}).encode("utf-8"))

    with pytest.raises(AssertionError, match="failed"):
        Contract().validate("GET", "/test/clock", response)


def test_contract_validator_rejects_missing_problem_field_errors():
    response = Response(
        400,
        "application/problem+json",
        json.dumps({"title": "Invalid request", "status": 400}).encode("utf-8"),
    )

    with pytest.raises(AssertionError, match="required failed"):
        Contract().validate("POST", "/tickets", response)
