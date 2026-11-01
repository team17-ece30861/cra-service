"""AC-16 locally through Django, plus the one check only visible from inside: logs."""

import logging

import pytest

from acceptance.client import Service
from acceptance.privacy_cases import SECRETS, PrivacyChecks
from tests.test_phase3_api import DjangoTransport


@pytest.fixture
def service():
    return Service(DjangoTransport())


@pytest.mark.django_db(transaction=True)
class TestLocalPrivacy(PrivacyChecks):
    @pytest.fixture(autouse=True)
    def no_reporter_in_logs(self, caplog):
        # App loggers at DEBUG; Django's own loggers keep their configured level (INFO).
        caplog.set_level(logging.DEBUG)
        yield
        # caplog.text at teardown holds only teardown records, so read each phase's.
        records = caplog.get_records("setup") + caplog.get_records("call")
        text = "\n".join(record.getMessage() for record in records)
        assert records, "no log records captured; the check would prove nothing"
        for value in SECRETS:
            assert value not in text
