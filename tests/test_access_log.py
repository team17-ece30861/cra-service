import runpy
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.test import Client
from gunicorn.config import Config
from gunicorn.glogging import Logger, SafeAtoms

from tests.conftest import TOKEN

pytestmark = pytest.mark.django_db

GUNICORN_CONF = runpy.run_path(str(Path(__file__).resolve().parent.parent / "gunicorn.conf.py"))
GUNICORN_LOGGER = Logger(Config())


def access_line(response) -> str:
    """The line gunicorn's access log writes for a test client response, built the
    way gunicorn.glogging.Logger.access builds it."""
    request = response.wsgi_request
    environ = {**request.environ, "RAW_URI": request.get_full_path()}
    req = SimpleNamespace(headers=[(k.upper(), v) for k, v in request.headers.items()])
    resp = SimpleNamespace(
        status=f"{response.status_code} {response.reason_phrase}",
        headers=list(response.items()),
        sent=len(response.content),
    )
    atoms = GUNICORN_LOGGER.atoms(resp, req, environ, timedelta(milliseconds=5))
    return GUNICORN_CONF["access_log_format"] % SafeAtoms(atoms)


def test_access_log_names_the_client_and_never_the_token(authed):
    line = access_line(authed.get("/test/clock"))
    assert " test [" in line
    assert '"GET /test/clock HTTP/1.1" 200' in line
    assert TOKEN not in line


def test_access_log_names_no_client_on_401():
    line = access_line(Client(headers={"Authorization": f"Bearer {TOKEN}x"}).get("/test/clock"))
    assert " - - [" in line
    assert '" 401 ' in line
    assert TOKEN not in line


def test_access_log_never_decodes_basic_credentials():
    # Gunicorn's default format logs the Basic username, which could be a token.
    authorization = "Basic dGVzdC10b2tlbjo="  # base64("test-token:")
    line = access_line(Client(headers={"Authorization": authorization}).get("/health"))
    assert TOKEN not in line
    assert "dGVzdC10b2tlbjo=" not in line
