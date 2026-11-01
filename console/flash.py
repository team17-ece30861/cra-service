"""A toast for the next page: a change that redirects leaves one, and the page it lands on
shows it once (docs/design.md, "Toasts")."""

KEY = "ledger_toast"


def flash(request, title: str, body: str = "") -> None:
    request.session[KEY] = {"title": title, "body": body}


def take(request) -> dict | None:
    """The waiting toast, if any; it's gone once taken."""
    return request.session.pop(KEY, None) if hasattr(request, "session") else None
