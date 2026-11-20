"""The portable 5.10 HTTP gap checks also run in CI through Django."""

import pytest

from acceptance.client import Service
from acceptance.http_gap_cases import HttpGapChecks
from tests.test_phase3_api import DjangoTransport


@pytest.fixture
def service():
    return Service(DjangoTransport())


@pytest.mark.django_db(transaction=True)
class TestLocalHttpGaps(HttpGapChecks):
    pass
