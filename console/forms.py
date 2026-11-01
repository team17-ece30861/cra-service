"""The New Ticket, Edit Ticket and Triage sheets (4.U2 part 2): which fields they show, how a
ticket fills them, how a posted form becomes one API request body, and how the API's
problem+json errors land back on the fields. Presentation only: the API judges every value
(docs/design.md, "Console rules that come from the API"). Field keys are the API's own
paths (``product.affected_versions``), which is also what ``?focus=`` takes."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import get_args

from django.core import signing
from django.urls import reverse

from console import present
from core.domain.deadlines import calculate_deadlines
from core.schemas import MemberState

SOURCES = [
    ("external_researcher", "External researcher"),
    ("customer", "Customer"),
    ("internal", "Internal"),
    ("scanner", "Scanner"),
    ("csirt", "CSIRT"),
]
SEVERITIES = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]
SENSITIVITIES = [(v, f"TLP:{v}") for v in ("CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED")]
MEMBER_STATES = list(get_args(MemberState))
DECISIONS = ("actively_exploited", "not_actively_exploited", "invalid")


@dataclass(frozen=True)
class Field:
    key: str  # the API path
    label: str
    kind: str = "text"  # text, long, select, list, time
    missing: str = ""  # copy for "required" / "must not be empty"
    format: str = ""  # copy for a value in the wrong shape


TIME_FORMAT = "Use the format 2026-10-29 14:00:00."
FIELDS = [
    Field("title", "Title", missing="Enter a title."),
    Field("source", "Source", "select", missing="Choose a source."),
    Field("product.manufacturer", "Manufacturer", missing="Enter the manufacturer."),
    Field("product.name", "Product", missing="Enter the product."),
    Field("product.affected_versions", "Affected versions", "list"),
    Field("description", "Description", "long", missing="Enter a description."),
    Field("reporter.name", "Name"),
    Field("reporter.contact", "Contact"),
    Field(
        "aware_at",
        "Aware since",
        "time",
        missing="Enter when your team became aware.",
        format=TIME_FORMAT,
    ),
    Field("change_reason", "Reason for the change", "long", missing="Enter a reason."),
    Field(
        "member_states",
        "Member states",
        "list",
        format="Use EU country codes, such as DE. Greece is GR.",
    ),
    Field("severity", "Severity", "select"),
    Field("sensitivity", "Sharing (TLP)", "select"),
    Field("vulnerability.cve_id", "CVE ID", format="Use the format CVE-2026-12345."),
    Field("vulnerability.description", "Vulnerability", "long"),
    Field("exploit.description", "Exploit", "long"),
    Field("mitigations.taken", "Mitigations taken", "long"),
    Field("mitigations.for_users", "Mitigations for users", "long"),
    Field("impact", "Impact", "long"),
    Field("malicious_actor", "Malicious actor", "long"),
    Field("fix.available_at", "Fix available", "time", format=TIME_FORMAT),
    Field("fix.fixed_versions", "Fixed versions", "list"),
    Field("fix.description", "Fix description", "long"),
]
BY_KEY = {f.key: f for f in FIELDS}
# Fields the Edit sheet compares with the ticket (source can't change; the reason isn't a field).
EDITABLE = [f.key for f in FIELDS if f.key not in ("source", "change_reason")]
# Optional groups the API stores as one object each.
GROUPS = ("reporter", "vulnerability", "exploit", "mitigations", "fix")

TRIAGE_FIELDS = {
    "decision": Field("decision", "Decision", missing="Choose a decision."),
    "aware_at": Field(
        "aware_at",
        "Aware since",
        "time",
        missing="Enter when your team became aware. Deadlines count from it.",
        format=TIME_FORMAT,
    ),
    "reason": Field("reason", "Reason", "long", missing="Enter what you checked and found."),
}

# One rule for times typed into the sheets, the same in forms.js (parseUtc): a date, a space
# or T, hours and minutes, optional seconds, then an optional UTC or Z, in any letter case.
_INPUT_TIME = re.compile(
    r"\s*([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?\s*(?:UTC|Z)?\s*",
    re.IGNORECASE,
)


def to_api_time(text: str) -> str:
    """'2026-10-29 14:00:00' (UTC, as the sheet asks for it) -> '2026-10-29T14:00:00Z'.
    Anything else goes to the API as typed, so the API's own error comes back."""
    m = _INPUT_TIME.fullmatch(text)
    if not m:
        return text.strip()
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s or '00'}Z"


def to_input_time(value: str | None) -> str:
    """'2026-10-29T14:00:00Z' -> '2026-10-29 14:00:00' for the field (its suffix says UTC)."""
    return value.replace("T", " ").removesuffix("Z") if value else ""


def _get(data: dict | None, path: str):
    for part in path.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def clean(text) -> str:
    """One rule for text on both sides of a comparison: browsers send textarea newlines as
    CRLF, and surrounding whitespace isn't a change."""
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def clean_list(items) -> list[str]:
    return [clean(v) for v in items or [] if clean(v)]


def values_from_ticket(ticket: dict) -> dict:
    """What the Edit sheet shows for a ticket, in the form's own terms (strings and lists)."""
    out = {}
    for f in FIELDS:
        value = _get(ticket, f.key)
        if f.kind == "list":
            out[f.key] = clean_list(value)
        elif f.kind == "time":
            out[f.key] = to_input_time(value)
        else:
            out[f.key] = clean(value)
    out["change_reason"] = ""
    return out


def values_from_post(post) -> dict:
    """The posted form, cleaned by the same rules. A list arrives as one value per line (the
    chips' hidden field), plus whatever was typed but not yet made a chip, comma-separated."""
    out = {}
    for f in FIELDS:
        if f.kind == "list":
            typed = re.split(r"[,\n]", post.get(f.key + "__add", ""))
            out[f.key] = clean_list(clean(post.get(f.key, "")).split("\n") + typed)
        else:
            out[f.key] = clean(post.get(f.key, ""))
    return out


# --- Edit: what the person changed, against what they saw ---

ORIGINAL_SALT = "console.edit-ticket.original"


def sign_original(values: dict) -> str:
    """The values the Edit sheet opened with, posted back with it (signed, so the page can't
    be made to claim a different starting point)."""
    return signing.dumps({k: values[k] for k in EDITABLE}, salt=ORIGINAL_SALT, compress=True)


def read_original(token: str) -> dict | None:
    try:
        data = signing.loads(token or "", salt=ORIGINAL_SALT)
    except signing.BadSignature:
        return None
    return data if isinstance(data, dict) and set(data) == set(EDITABLE) else None


def changed_keys(original: dict, values: dict) -> list[str]:
    return [k for k in EDITABLE if values[k] != original[k]]


def conflicts(changed: list[str], original: dict, current: dict, values: dict) -> list[str]:
    """Fields this person changed that someone else also changed since the sheet opened."""
    return [k for k in changed if current[k] != original[k] and current[k] != values[k]]


def merged(changed: list[str], values: dict, current: dict) -> dict:
    """The ticket as it is now, with this person's changes on top: what the sheet shows next."""
    return {**current, **{k: values[k] for k in changed}, "change_reason": values["change_reason"]}


def _api_value(f: Field, value):
    return to_api_time(value) if f.kind == "time" and value else value


def create_body(values: dict) -> dict:
    """POST /tickets: every filled field; empty ones are left out (the API says what's required)."""
    body: dict = {}
    for f in FIELDS:
        if f.key in ("aware_at", "change_reason"):
            continue
        value = values.get(f.key)
        if not value:
            continue
        top, _, sub = f.key.partition(".")
        if sub:
            body.setdefault(top, {})[sub] = _api_value(f, value)
        else:
            body[top] = _api_value(f, value)
    body.setdefault("product", {})
    return body


def update_body(changed: list[str], values: dict) -> dict:
    """PATCH /tickets/{id}: only the fields the person changed (``values`` is the ticket as
    it is now with their changes on top). An emptied optional field is cleared with null; a
    group whose fields are all empty is cleared whole. The API can't clear one field inside a
    group while keeping the rest (subfields aren't nullable), so that goes as "" and the
    API's answer is shown under the field."""
    body: dict = {}
    for key in changed:
        f = BY_KEY[key]
        top, _, sub = key.partition(".")
        value = _api_value(f, values[key])
        if not sub:
            keep = f.kind == "list" or key in ("title", "description", "aware_at")
            body[top] = value if keep else (value or None)
        elif top in GROUPS and all(not values[k] for k in BY_KEY if k.startswith(top + ".")):
            body[top] = None
        elif body.get(top, {}) is not None:
            body.setdefault(top, {})[sub] = value
    if body and values.get("change_reason"):
        body["change_reason"] = values["change_reason"]
    return body


def triage_body(post) -> dict:
    body = {}
    decision = post.get("decision", "")
    if decision:
        body["decision"] = decision
    reason = clean(post.get("reason", ""))
    if reason:
        body["reason"] = reason
    aware = post.get("aware_at", "").strip()
    if decision == "actively_exploited" and aware:
        body["aware_at"] = to_api_time(aware)
    return body


@dataclass
class Problems:
    """The API's answer to a failed change, placed on the sheet: one line per field, and
    anything that isn't about a field shown once at the top."""

    fields: dict = field(default_factory=dict)
    general: str = ""
    title: str = ""

    def __bool__(self):
        return bool(self.fields or self.general)


def _say(f: Field | None, message: str, now: datetime) -> str:
    if message in ("required", "must not be empty") or message.startswith("required "):
        if f and f.missing:
            return f.missing
        return f"{f.label} can't be empty." if f else "This can't be empty."
    if message.startswith("must not be later than"):
        when = now.strftime("%Y-%m-%d %H:%M:%S")
        return f"That's later than now. Enter a time at or before {when} UTC."
    shape = ("must match the pattern", "must be one of", "must be an RFC 3339", "must include")
    if f and f.format and message.startswith(shape):
        return f.format
    if message == "must contain unique member states":
        return "Each member state can appear once."
    text = message[:1].upper() + message[1:]
    return text if text.endswith(".") else text + "."


def problems(result, known: dict, now: datetime) -> Problems:
    """Map an ApiResult error onto the sheet's fields (``known``: key -> Field)."""
    data = result.data or {}
    out = Problems(title=data.get("title", ""))
    for e in data.get("errors") or []:
        key = re.sub(r"\[\d+\]", "", e.get("field", ""))
        f = known.get(key)
        message = _say(f or BY_KEY.get(key), e.get("message", ""), now)
        if f:
            out.fields.setdefault(key, message)
        else:
            label = (BY_KEY.get(key) or Field(key, key)).label
            out.general = out.general or f"{label}: {message[:1].lower()}{message[1:]}"
    if not out.fields and not out.general:
        out.general = data.get("detail") or "That didn't work. Nothing was changed."
    return out


GROUP_NAME = {"vulnerability": "vulnerability", "mitigations": "mitigation", "fix": "fix"}


def explain_partial_clears(problems: Problems, initial: dict, values: dict) -> None:
    """A field emptied inside a group whose other fields stay filled: the API can't clear
    it on its own (PATCH merges groups one level deep; their fields aren't nullable), so
    say what will work instead of echoing its "can't be empty"."""
    for key in list(problems.fields):
        top, _, sub = key.partition(".")
        if top in GROUP_NAME and sub and initial.get(key) and not values.get(key):
            problems.fields[key] = (
                f"This can't be cleared while other {GROUP_NAME[top]} details are filled in. "
                "Enter a value, or clear them too."
            )


def deadline_offsets() -> dict:
    """Seconds from awareness to each report's due time, read from the domain's own
    calculation (core/domain/deadlines.py) so the triage preview can't drift from it.
    The final report depends on the fix, so the preview leaves it out."""
    # Not a copy of the rule: the domain function itself, run on a fixed time (agreed 2026-11-01).
    ref = datetime.fromisoformat("2026-01-01T00:00:00+00:00")
    d = calculate_deadlines(ref)
    return {
        "early_warning": int((d.early_warning_due - ref).total_seconds()),
        "notification": int((d.notification_due - ref).total_seconds()),
    }


def hours(seconds: int) -> str:
    return f"{seconds // 3600} h"


# --- What the sheet templates get ---

MORE = {
    "member_states",
    "severity",
    "sensitivity",
    "vulnerability.cve_id",
    "vulnerability.description",
    "exploit.description",
    "mitigations.taken",
    "mitigations.for_users",
    "impact",
    "malicious_actor",
    "fix.available_at",
    "fix.fixed_versions",
    "fix.description",
}
NEW_KNOWN = {k: f for k, f in BY_KEY.items() if k not in ("aware_at", "change_reason")}
GENERAL_TITLE = {
    "new": "The ticket wasn't created",
    "edit": "Nothing was saved",
    "triage": "The ticket wasn't triaged",
}


def edit_known(ticket: dict) -> dict:
    return {
        k: f
        for k, f in BY_KEY.items()
        if k != "source" and (k != "aware_at" or ticket.get("aware_at"))
    }


def _nest(flat: dict) -> dict:
    out: dict = {}
    for key, value in flat.items():
        top, _, sub = key.partition(".")
        if sub:
            out.setdefault(top, {})[sub] = value
        else:
            out[top] = value
    return out


def _shown(values: dict) -> dict:
    return {k: "\n".join(v) if isinstance(v, list) else v for k, v in values.items()}


def blank() -> dict:
    return {f.key: [] if f.kind == "list" else "" for f in FIELDS}


def ticket_form(mode, *, values, initial=None, problems=None, ticket=None, focus="") -> dict:
    """The New Ticket or Edit Ticket sheet (one form, two modes, as in the prototype)."""
    p = problems or Problems()
    edit = mode == "edit"
    focus = focus if focus in BY_KEY else ""
    more_open = edit or focus in MORE or any(k in MORE for k in p.fields)
    more_open = more_open or any(values.get(k) for k in MORE)
    return {
        "mode": mode,
        "p": "te" if edit else "tn",
        "action": reverse("console:edit-ticket", args=[ticket["id"]])
        if edit
        else reverse("console:new-ticket"),
        "base": reverse("console:ticket", args=[ticket["id"]])
        if edit
        else reverse("console:tickets"),
        "v": _nest(_shown(values)),
        "i": _nest(_shown(initial)) if initial else {},
        "original": sign_original(initial) if edit and initial else "",
        "e": _nest(p.fields),
        "general": p.general,
        "general_title": GENERAL_TITLE[mode],
        "show_aware": bool(edit and ticket and ticket.get("aware_at")),
        "source_label": present.SOURCE_LABEL.get(ticket.get("source"), "") if ticket else "",
        "focus": focus,
        "more_open": more_open,
        "sources": SOURCES,
        "severities": SEVERITIES,
        "sensitivities": SENSITIVITIES,
        "member_states": " ".join(MEMBER_STATES),
    }


def triage_form(ticket: dict, *, post=None, problems=None) -> dict:
    p = problems or Problems()
    post = post or {}
    offsets = deadline_offsets()
    return {
        "action": reverse("console:triage", args=[ticket["id"]]),
        "base": reverse("console:ticket", args=[ticket["id"]]),
        "decision": post.get("decision", "") if post.get("decision") in DECISIONS else "",
        "aware": post.get("aware_at", ""),
        "reason": post.get("reason", ""),
        "e": p.fields,
        "general": p.general,
        "general_title": GENERAL_TITLE["triage"],
        "ew_after": hours(offsets["early_warning"]),
        "n_after": hours(offsets["notification"]),
        "offsets": offsets,
        "title": ticket["title"],
        "product": (ticket.get("product") or {}).get("name", ""),
        "received": present.utc(ticket.get("received_at")),
        "state": ticket["state"],
        "state_label": present.STATE_LABEL.get(ticket["state"], ticket["state"]),
    }


def new_sheet(values=None, problems=None) -> dict:
    return {"tf_new": ticket_form("new", values=values or blank(), problems=problems)}


def ticket_sheets(ticket: dict) -> dict:
    """The sheets the Ticket page carries, closed until opened (in place, or by URL)."""
    current = values_from_ticket(ticket)
    return {
        **new_sheet(),
        "tf_edit": ticket_form("edit", values=current, initial=current, ticket=ticket),
        "tr": triage_form(ticket),
    }
