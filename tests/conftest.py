import pytest
from django.test import Client

TOKEN = "test-token"


@pytest.fixture(autouse=True)
def api_token(settings):
    # Tests never depend on the shell's API_TOKEN (CI doesn't set one).
    settings.API_TOKEN = TOKEN
    return TOKEN


@pytest.fixture
def authed():
    """A client that sends the bearer token on every request."""
    return Client(headers={"Authorization": f"Bearer {TOKEN}"})
