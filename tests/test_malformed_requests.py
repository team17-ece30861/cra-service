"""AC-13 (REQ-12): at least 500 malformed requests generated from openapi.yaml.

Runs the corpus from acceptance/malformed.py through the in-process app (Django test
client, full middleware stack). Every request must get the status the contract's
precedence gives, as problem+json matching the contract, never a 5xx, and no stored
row may change. The same corpus runs against a deployment with
`python -m acceptance.malformed`.
"""

import os
import subprocess
import sys
import time

import pytest
from django.test import Client

from acceptance.client import ROOT, Response, Service
from acceptance.malformed import (
    MINIMUM_FAULTS,
    PYTHON,
    UNGENERATED,
    expected_corpus,
    fingerprint,
    generate,
    observable_state,
    print_summary,
    run,
    seed_tickets,
    summarize,
)
from core.models import AuditEntry, FixedClock, ReportSubmission, Ticket
from tests.conftest import TOKEN
from tests.test_phase3_api import DjangoTransport


def django_sender(method, path, headers, body):
    headers = dict(headers)
    content_type = headers.pop("Content-Type", None)
    extra = {"content_type": content_type} if content_type is not None else {}
    response = Client(raise_request_exception=False).generic(
        method,
        path,
        body or b"",
        headers={**headers, "Authorization": f"Bearer {TOKEN}"},
        **extra,
    )
    return Response(response.status_code, response.get("Content-Type", ""), response.content)


def stored_rows():
    return {
        model.__name__: list(model.objects.order_by("pk").values())
        for model in (Ticket, AuditEntry, ReportSubmission, FixedClock)
    }


@pytest.fixture(scope="module")
def generated():
    return generate()


def test_corpus_is_the_recorded_one(generated):
    """Every run on one operating system sends the recorded corpus. A different Python or
    library version, or a change to openapi.yaml, gives a different corpus: regenerate and
    update the recorded values in acceptance/malformed.py on purpose, never to get green."""
    corpus, _ = generated
    assert sys.version_info[:2] == PYTHON
    assert len({request.fault for request in corpus}) == len(corpus) >= MINIMUM_FAULTS
    expected = expected_corpus()
    if expected is None:
        pytest.skip(f"no corpus is recorded for {sys.platform}")
    assert (len(corpus), fingerprint(corpus)) == expected


def test_generation_matches_a_fresh_interpreter(generated):
    """Generation inside pytest once differed from a plain interpreter (Hypothesis drew
    constants from loaded test modules), so check against the CLI's context directly."""
    in_process = fingerprint(generated[0])
    fresh = subprocess.run(
        [
            sys.executable,
            "-c",
            "from acceptance.malformed import fingerprint, generate; "
            "print(fingerprint(generate()[0]))",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONHASHSEED": "1"},
    )
    assert fresh.stdout.strip() == in_process


@pytest.mark.django_db(transaction=True)
def test_ac13_generated_malformed_requests(generated, capsys):
    corpus, stats = generated
    operations = {request.operation for request in corpus}
    distinct = len({request.fault for request in corpus})
    assert distinct >= MINIMUM_FAULTS, f"only {distinct} distinct malformed requests"
    assert len(operations) == 7 and not operations & set(UNGENERATED)

    service = Service(DjangoTransport())
    seeds = seed_tickets(service)
    rows_before = stored_rows()
    api_before = observable_state(service, seeds)

    started = time.monotonic()
    outcome = run(service, django_sender, corpus, seeds)
    seconds = time.monotonic() - started

    api_after = observable_state(service, seeds)
    rows_after = stored_rows()
    summary = summarize(corpus, stats, outcome, api_before, api_after, seconds)
    with capsys.disabled():
        print()
        print_summary(summary, show=5)

    assert summary["requests_sent"] == len(corpus)
    assert summary["server_errors"] == 0
    assert not summary["failures"], summary["failures"][:5]
    assert all(400 <= int(status) < 500 for status in summary["by_status"])
    assert summary["data_unchanged"]
    assert rows_after == rows_before
