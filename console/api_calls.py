"""Console pages reach the API by running its own views in-process, so validation,
errors and audit entries are exactly the API's, with no token and no network hop.
The signed-in username is the X-Actor on every call (docs/plan.md, 4.U1)."""

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from django.db import transaction
from django.http import HttpRequest
from django.test import RequestFactory
from django.urls import resolve

from cra_service.validation import ACTOR_HEADER

_factory = RequestFactory()


@dataclass(frozen=True)
class ApiResult:
    status: int
    data: Any

    @property
    def ok(self) -> bool:
        return self.status < 400


def call_api(request: HttpRequest, method: str, path: str, *, body=None, query=None) -> ApiResult:
    """Runs one API operation as the signed-in person. A failed call changes nothing:
    it runs in its own savepoint, rolled back when the API answers with an error."""
    url = path + ("?" + urlencode(query, doseq=True) if query else "")
    headers = {ACTOR_HEADER: request.user.get_username()}
    inner = _factory.generic(
        method,
        url,
        data=json.dumps(body) if body is not None else "",
        content_type="application/json",
        headers=headers,
    )
    inner.client_name = "console"
    match = resolve(path)
    with transaction.atomic():
        response = match.func(inner, *match.args, **match.kwargs)
        if response.status_code >= 400:
            transaction.set_rollback(True)
    data = json.loads(response.content) if response.content else None
    return ApiResult(response.status_code, data)
