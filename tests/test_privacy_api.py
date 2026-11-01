"""AC-16 locally through Django, plus the one check only visible from inside: logs."""

import logging

import pytest

from acceptance.client import Service
from acceptance.privacy_cases import LATER_SECRET, SECRET, SECRET_NAME, PrivacyChecks
from tests.test_phase3_api import DjangoTransport


@pytest.fixture
def service():
    return Service(DjangoTransport())


@pytest.mark.django_db(transaction=True)
class TestLocalPrivacy(PrivacyChecks):
    @pytest.fixture(autouse=True)
    def no_reporter_in_logs(self, caplog):
        caplog.set_level(logging.DEBUG)
        yield
        for value in (SECRET, SECRET_NAME, LATER_SECRET):
            assert value not in caplog.text
