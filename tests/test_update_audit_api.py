"""Q6 cases run locally through Django."""

import pytest

from acceptance.client import Service
from acceptance.update_cases import UpdateAuditChecks
from tests.test_phase3_api import DjangoTransport


@pytest.fixture
def service():
    return Service(DjangoTransport())


@pytest.mark.django_db(transaction=True)
class TestLocalUpdateAudit(UpdateAuditChecks):
    pass
