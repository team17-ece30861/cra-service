"""Database connections through Neon's transaction-mode pooler (cra_service/settings.py):
kept for DB_CONN_MAX_AGE seconds in the Docker image, health-checked, bounded connect
attempts, and never prepared statements or server-side cursors, which PgBouncer in
transaction mode can't carry between transactions."""

from pathlib import Path

import pytest
from django.db import connection

from cra_service.settings import database_settings

pytestmark = pytest.mark.django_db

URL = {"DATABASE_URL": "postgresql://u:p@db.example:5432/app?sslmode=require"}


def test_connections_persist_for_db_conn_max_age_and_are_health_checked():
    database = database_settings({**URL, "DB_CONN_MAX_AGE": "300"})
    assert database["CONN_MAX_AGE"] == 300
    assert database["CONN_HEALTH_CHECKS"] is True


def test_without_db_conn_max_age_each_request_gets_a_new_connection():
    # runserver's thread per connection would leak kept connections.
    assert database_settings(URL)["CONN_MAX_AGE"] == 0


def test_the_docker_image_keeps_connections():
    dockerfile = (Path(__file__).resolve().parent.parent / "Dockerfile").read_text()
    assert "DB_CONN_MAX_AGE=300" in dockerfile


def test_pooler_safe_options_keep_the_url_options():
    database = database_settings(URL)
    assert database["DISABLE_SERVER_SIDE_CURSORS"] is True
    assert database["OPTIONS"] == {
        "sslmode": "require",
        "prepare_threshold": None,
        "server_side_binding": False,
        "connect_timeout": 10,
    }


def test_live_connection_params_time_out_and_never_prepare():
    params = connection.get_connection_params()
    assert params["connect_timeout"] == 10
    assert params["prepare_threshold"] is None
    # Client-side binding: Django's ClientCursor, not psycopg's server-binding cursor.
    assert params["cursor_factory"].__name__ == "Cursor"
    assert connection.settings_dict["CONN_HEALTH_CHECKS"] is True


def test_queries_are_not_prepared_on_the_server():
    with connection.cursor() as cursor:
        for _ in range(10):  # psycopg prepares after 5 runs when a threshold is set
            cursor.execute("SELECT %s::int", [1])
        cursor.execute("SELECT count(*) FROM pg_prepared_statements")
        assert cursor.fetchone() == (0,)
