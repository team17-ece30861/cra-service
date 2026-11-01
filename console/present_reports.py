"""How the report pages show what the API returns (4.U3): the Report Draft page, the Record
Submission sheet and the Close Ticket dialog. Presentation only: labels, field order, copy and
the time format people type. Which fields are required or missing, every status and every
deadline come from the API's response (docs/design.md, "Console rules that come from the API")."""

import re

from console import present
from cra_service.timestamps import parse_timestamp

REPORT_TYPES = ("early_warning", "notification", "final_report", "user_advisory")
LABEL = {**present.REPORT_LABEL, "user_advisory": "User advisory"}
TITLE = {**present.REPORT_TITLE, "user_advisory": "User Advisory"}
# The tabs' short labels on phones, as the prototype.
SHORT = {
    "early_warning": "Early",
    "notification": "Notification",
    "final_report": "Final",
    "user_advisory": "Advisory",
}

# Draft fields in the order a report reads (the prototype's MODEL), with the names people know.
FIELDS = (
    ("product.manufacturer", "Manufacturer"),
    ("product.name", "Product"),
    ("product.affected_versions", "Affected versions"),
    ("member_states", "Member states"),
    ("vulnerability.cve_id", "CVE ID"),
    ("vulnerability.description", "Vulnerability"),
    ("exploit.description", "Exploit"),
    ("mitigations.taken", "Mitigations taken"),
    ("mitigations.for_users", "Mitigations for users"),
    ("sensitivity", "Sharing (TLP)"),
    ("severity", "Severity"),
    ("impact", "Impact"),
    ("malicious_actor", "Malicious actor"),
    ("fix.available_at", "Fix available"),
    ("fix.description", "Fix description"),
    ("fix.fixed_versions", "Fixed versions"),
)
FIELD_LABEL = dict(FIELDS)
# Draft content that describes the report rather than being one of its fields.
META_FIELDS = ("ticket_id", "aware_at")
SUBMITTED = ("submitted", "submitted_late")

# The time people type: "2026-10-29 14:00:00" in UTC (a "T", a "Z" or " UTC" are fine too).
_UI_TIME = re.compile(
    r"\s*([0-9]{4}-[0-9]{2}-[0-9]{2})[ Tt]([0-9]{2}:[0-9]{2})(?::([0-9]{2}))?\s*(?:UTC|Z)?\s*",
    re.IGNORECASE,
)
TIME_EXAMPLE = "2026-10-29 14:00:00"


def field_label(path: str) -> str:
    return FIELD_LABEL.get(path, path.replace("_", " ").replace(".", " ").capitalize())


def ui_time(value: str | None) -> str:
    """2026-10-29T14:00:00Z -> 2026-10-29 14:00:00 (the input shows UTC beside it)."""
    return present.utc(value).removesuffix(" UTC")


def api_time(value: str) -> str:
    """What people type -> the API's RFC 3339 form. Anything else goes to the API as typed,
    so the API's own check decides and its error is shown."""
    match = _UI_TIME.fullmatch(value)
    if not match:
        return value
    date, hour_minute, second = match.groups()
    return f"{date}T{hour_minute}:{second or '00'}Z"


def _flatten(content: dict) -> dict:
    out = {}
    for key, value in content.items():
        if key in META_FIELDS:
            continue
        if isinstance(value, dict):
            for sub, inner in value.items():
                out[f"{key}.{sub}"] = inner
        else:
            out[key] = value
    return out


def _show(path: str, value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if path == "fix.available_at":
        return present.utc(value)
    if path == "sensitivity":
        return f"TLP:{value}"
    if path == "severity":
        return str(value).capitalize()
    return str(value)


def draft_rows(draft: dict) -> list[dict]:
    """One row per field the draft has, plus one per field the API says is missing, in
    report order. A field the API left out and doesn't call missing isn't shown."""
    values = _flatten(draft.get("content") or {})
    missing = list(draft.get("missing_fields") or [])
    order = [p for p, _ in FIELDS]
    paths = [p for p in order if p in values or p in missing]
    paths += [p for p in list(values) + missing if p not in order and p not in paths]
    return [
        {
            "path": path,
            "label": field_label(path),
            "missing": path in missing,
            "value": "" if path in missing else _show(path, values[path]),
        }
        for path in paths
    ]


def copy_text(draft: dict, rows: list[dict]) -> str:
    """The report as plain text for the authority's form: what Copy Report puts on the clipboard."""
    content = draft.get("content") or {}
    lines = [f"{LABEL[draft['type']]} · ticket {draft['ticket_id']}"]
    if content.get("aware_at"):
        lines.append(f"Aware since {present.utc(content['aware_at'])}")
    lines += [f"{r['label']}: {r['value']}" for r in rows if not r["missing"]]
    return "\n".join(lines)


def badge(status: str | None) -> dict | None:
    if status not in present.STATUS:
        return None
    cls, icon, label = present.STATUS[status]
    return {"cls": cls, "icon": icon, "label": label}


def draft_view(draft: dict, now) -> dict:
    """The Report Draft page's header, banner and fields for one draft."""
    kind = draft["type"]
    status = draft.get("status")
    locked = draft.get("submitted_at") is not None
    rows = draft_rows(draft)
    missing = [r for r in rows if r["missing"]]
    if locked:
        banner = "locked"
    elif kind == "user_advisory":
        banner = "advisory"
    elif missing:
        banner = "missing"
    else:
        banner = "ready"
    return {
        "type": kind,
        "label": LABEL[kind],
        "title": TITLE[kind],
        "badge": badge(status),
        "status": status,
        "due_at": draft.get("due_at"),
        "due": present.utc(draft.get("due_at")),
        "rel": present.relative((parse_timestamp(draft["due_at"]) - now).total_seconds())
        if draft.get("due_at")
        else "",
        "awaiting_fix": status == "awaiting_fix",
        "locked": locked,
        "submitted": present.utc(draft.get("submitted_at")),
        "reference": draft.get("reference"),
        "aware_at": (draft.get("content") or {}).get("aware_at"),
        "aware": present.utc((draft.get("content") or {}).get("aware_at")),
        "banner": banner,
        "rows": rows,
        "missing": missing,
        "recordable": not locked and kind != "user_advisory",
        "record_blocked": bool(missing) or status == "awaiting_fix",
        "copy": copy_text(draft, rows),
    }


def tabs(ticket_id: str, current: str) -> list[dict]:
    return [
        {"type": t, "title": TITLE[t], "short": SHORT[t], "on": t == current} for t in REPORT_TYPES
    ]


def record_errors(problem: dict | None, aware: str) -> tuple[dict, list[str], str]:
    """Splits an API problem into messages under the two fields, the fields still missing,
    and one message for the rest. The API decides; this only words it for people."""
    problem = problem or {}
    fields, missing, other = {}, [], []
    for e in problem.get("errors") or []:
        field, message = e.get("field", ""), e.get("message", "")
        if field == "submitted_at":
            if message == "must be between aware_at and now":
                fields[field] = (
                    f"Enter a time between when your team became aware ({aware}) and now."
                    if aware
                    else "Enter a time between when your team became aware and now."
                )
            elif message == "is not a valid date and time":
                fields[field] = "That isn't a real date and time."
            else:
                fields[field] = f"Use the format {TIME_EXAMPLE}."
        elif field == "reference":
            fields[field] = f"The reference {message}."
        elif message == "required for this report":
            missing.append(field)
        else:
            other.append(f"{field} {message}".strip())
    single = problem.get("detail") or ""
    if other and not single:
        single = "The service didn't accept this: " + "; ".join(other) + "."
    return fields, missing, single


def close_view(ticket: dict) -> dict:
    """The Close Ticket dialog for a ticket as the API returned it: ready, not ready (with the
    reports still to record, by their API status), or already closed."""
    # Mirrors the closure rule in core/domain/closure.py; tests/test_console_reports checks it.
    state = ticket.get("state")
    obligations = ticket.get("obligations") or {}
    left = []
    for r in present.REPORTS:
        ob = obligations.get(r) or {}
        if ob.get("status") not in SUBMITTED:
            left.append({"label": present.REPORT_LABEL[r], "badge": badge(ob.get("status"))})
    if state == "closed":
        resolution = present.RESOLUTION_LABEL.get(ticket.get("resolution") or "", "")
        variant = "closed"
        body = "It's already closed" + (f" as {resolution.lower()}." if resolution else ".")
        left = []
    elif state != "reportable":
        variant = "blocked"
        body = (
            "A ticket can close once it's triaged as actively exploited "
            "and all three reports are submitted."
        )
        left = []
    elif left:
        variant = "blocked"
        body = "A ticket can close once all three reports are submitted. Still to record:"
    else:
        variant = "ready"
        body = (
            "All three reports are submitted. Closing marks the ticket resolved and adds a "
            "closed entry to the audit trail. It can't be reopened."
        )
    return {"variant": variant, "body": body, "left": left}
