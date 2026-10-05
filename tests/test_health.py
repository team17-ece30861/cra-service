from django.test import Client


def test_health_returns_ok():
    response = Client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_needs_no_auth():
    response = Client().get("/health")
    assert response.status_code != 401
