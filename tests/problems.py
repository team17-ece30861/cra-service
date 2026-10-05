PROBLEM = "application/problem+json"


def assert_problem(response, status: int, title: str) -> dict:
    """Assert `response` is an RFC 9457 problem as openapi.yaml defines it."""
    assert response.status_code == status, response.content
    assert response["Content-Type"] == PROBLEM
    body = response.json()
    assert body["title"] == title
    assert body["status"] == status
    if status in (400, 422):
        assert body["errors"], "400 and 422 need at least one {field, message}"
        for error in body["errors"]:
            assert set(error) == {"field", "message"}
            assert isinstance(error["field"], str) and isinstance(error["message"], str)
    return body
