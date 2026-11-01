"""How console pages show what the API returns. Presentation only: labels, groups by due
window, countdown text. Every status, deadline and state comes from the API's response;
nothing here decides a business rule (docs/design.md, "Console rules that come from the API")."""

from datetime import datetime, timedelta

from django.urls import reverse

from cra_service.timestamps import format_timestamp, parse_timestamp

REPORTS = ("early_warning", "notification", "final_report")
REPORT_LABEL = {
    "early_warning": "Early warning",
    "notification": "Notification",
    "final_report": "Final report",
}
# Controls use Title Case (docs/design.md, "Casing").
REPORT_TITLE = {
    "early_warning": "Early Warning",
    "notification": "Notification",
    "final_report": "Final Report",
}
REPORT_SHORT = {"early_warning": "EW", "notification": "N", "final_report": "FR"}

# Obligation status -> (class, icon, label), as the prototype's badges and track chips.
STATUS = {
    "not_applicable": ("na", "i-minus", "Not required"),
    "awaiting_fix": ("await", "i-hourglass", "Waiting on fix"),
    "pending": ("pending", "i-clock", "Due"),
    "overdue": ("overdue", "i-alert", "Overdue"),
    "submitted": ("submitted", "i-check", "Submitted"),
    "submitted_late": ("late", "i-check", "Submitted late"),
}
STATE_LABEL = {"received": "Received", "reportable": "Reportable", "closed": "Closed"}
RESOLUTION_LABEL = {
    "resolved": "Resolved",
    "not_actively_exploited": "Not actively exploited",
    "invalid": "Invalid",
}
SOURCE_LABEL = {
    "external_researcher": "External researcher",
    "customer": "Customer",
    "internal": "Internal",
    "scanner": "Scanner",
    "csirt": "CSIRT",
}
TLP_CLASS = {
    "CLEAR": "",
    "GREEN": "green",
    "AMBER": "amber",
    "AMBER+STRICT": "amberstrict",
    "RED": "red",
}
AUDIT_ICON = {
    "created": "i-plus",
    "triaged": "i-shield",
    "updated": "i-pencil",
    "report_submitted": "i-send",
    "closed": "i-archive",
}
DAY = timedelta(hours=24)


def utc(value: str | None) -> str:
    """2026-10-30T09:12:00Z -> 2026-10-30 09:12:00 UTC (the API already gives UTC to the second)."""
    if not value:
        return ""
    return format_timestamp(parse_timestamp(value)).replace("T", " ").replace("Z", " UTC")


def iso(moment: datetime) -> str:
    return format_timestamp(moment)


def hms(seconds: float, two: bool = False) -> str:
    """The prototype's hmsStr: hours (two digits on the hero), minutes, seconds. Counts the
    time left, or the time since an overdue deadline."""
    s = int(abs(seconds))
    h = s // 3600
    return (f"{h:02d}" if two else str(h)) + f":{s // 60 % 60:02d}:{s % 60:02d}"


def relative(seconds: float) -> str:
    """The prototype's relStr: 'in 6 h 40 m', 'in 1 d 18 h', '2 h 5 m overdue'."""
    late = seconds < 0
    m = int(abs(seconds) // 60)
    d, h = m // 1440, m // 60 % 24
    text = f"{d} d {h} h" if d else f"{m // 60} h {m % 60} m"
    return f"{text} overdue" if late else f"in {text}"


def span(seconds: float) -> str:
    """A length of time, rounded to the hour: '72 h', '14 d'."""
    hours = round(seconds / 3600)
    return f"{hours // 24} d" if hours >= 7 * 24 and hours % 24 == 0 else f"{hours} h"


def initials(username: str) -> str:
    parts = [p for p in "".join(c if c.isalnum() else " " for c in username).split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (username[:2] or "?").upper()


def next_report(ticket: dict) -> str | None:
    """The report whose due time is the ticket's next_due_at, as the API returned it."""
    due = ticket.get("next_due_at")
    if due is None:
        return None
    for report in REPORTS:
        ob = ticket["obligations"][report]
        if ob["due_at"] == due and ob["submitted_at"] is None:
            return report
    return None


def track(ticket: dict) -> list[dict]:
    return [
        {"short": REPORT_SHORT[r], "cls": STATUS[ticket["obligations"][r]["status"]][0]}
        for r in REPORTS
    ]


def row(ticket: dict, now: datetime) -> dict:
    """One list row: the ticket, its report track and its deadline chip."""
    report = next_report(ticket)
    due = ticket.get("next_due_at")
    seconds = (parse_timestamp(due) - now).total_seconds() if due else None
    product = ticket.get("product") or {}
    if ticket["state"] == "received":
        chip, action = "Needs triage", "Triage"
    elif ticket["state"] == "closed":
        chip, action = "Closed · " + RESOLUTION_LABEL.get(ticket.get("resolution"), ""), None
        chip = chip.rstrip(" ·")
    elif report:
        chip, action = REPORT_LABEL[report], "Record " + REPORT_TITLE[report]
    elif ticket["obligations"]["final_report"]["status"] == "awaiting_fix":
        chip, action = "Final report · waiting on fix", "Edit Ticket"
    else:
        chip, action = "All reports submitted", "Close Ticket"
    return {
        "id": ticket["id"],
        "title": ticket["title"],
        "product": product.get("name", ""),
        "track": track(ticket),
        "report": report,
        "report_label": REPORT_LABEL.get(report, ""),
        "report_short": REPORT_SHORT.get(report, ""),
        "report_cls": STATUS[ticket["obligations"][report]["status"]][0] if report else "",
        "count": hms(seconds) if seconds is not None else "",
        "count2": hms(seconds, two=True) if seconds is not None else "",
        "track_label": ", ".join(
            f"{REPORT_LABEL[r]} {STATUS[ticket['obligations'][r]['status']][2].lower()}"
            for r in REPORTS
        ),
        "due": due,
        "rel": relative(seconds) if seconds is not None else "",
        "rel_cls": "late"
        if seconds is not None and seconds < 0
        else "soon"
        if seconds is not None and seconds < 12 * 3600
        else "",
        "seconds": seconds,
        "chip": chip,
        "action": action,
        "action_href": _sheet_href(ticket["id"], action),
        "state": ticket["state"],
    }


def _sheet_href(ticket_id: str, action: str | None) -> str:
    """The row actions that open a sheet (console/views_forms.py)."""
    if action == "Triage":
        return reverse("console:triage", args=[ticket_id])
    if action == "Edit Ticket":
        return reverse("console:edit-ticket", args=[ticket_id]) + "?focus=fix.available_at"
    return ""


def rows(tickets: list[dict], now: datetime) -> list[dict]:
    """Every ticket's row, built once per request and shared by the list, the island and
    the dock."""
    return [row(t, now) for t in tickets]


def group_rows(rows: list[dict]) -> list[dict]:
    """Rows grouped by due window, in the API's order within each group. Grouping is
    presentation from next_due_at; closed tickets are left to their own view."""
    groups = {
        "overdue": ("Overdue", []),
        "today": ("Due in 24 h", []),
        "later": ("Later", []),
        "triage": ("To triage", []),
        "waiting": ("Nothing due", []),
        "closed": ("Closed", []),
    }
    for r in rows:
        if r["state"] == "closed":
            key = "closed"
        elif r["state"] == "received":
            key = "triage"
        elif r["seconds"] is None:
            key = "waiting"
        elif r["seconds"] < 0:
            key = "overdue"
        elif r["seconds"] < DAY.total_seconds():
            key = "today"
        else:
            key = "later"
        groups[key][1].append(r)
    return [
        {"key": key, "title": title, "rows": members}
        for key, (title, members) in groups.items()
        if members
    ]


def deadlines(rows: list[dict]) -> list[dict]:
    """Every open ticket's next deadline, soonest first (the island and the hero)."""
    out = [r for r in rows if r["report"] and r["state"] != "closed"]
    out.sort(key=lambda r: r["due"])
    return out


# The command field lists the suggestions, then at most this many tickets in the API's
# order (most urgent first), so a long list doesn't put every ticket on every page.
COMMAND_TICKETS = 20


def shell(rows: list[dict], groups: list[dict], upcoming: list[dict]) -> dict:
    """What every signed-in page shows around its content: the island, the dock's counts,
    and the command field's suggestions. Takes the rows, groups and deadlines already
    built for the request."""
    by_key = {g["key"]: g["rows"] for g in groups}
    commands = []
    for r in upcoming[:2]:
        commands.append(
            {
                "icon": "i-send",
                "text": f"{r['action']} · {r['title']}",
                "hint": r["rel"].replace("in ", "due in ", 1),
                "soon": r["action"],
                "id": r["id"],
                "record": r["report"],
            }
        )
    for r in by_key.get("triage", [])[:1]:
        commands.append(
            {
                "icon": "i-shield",
                "text": f"Triage · {r['title']}",
                "hint": "received",
                "sheet": reverse("console:triage", args=[r["id"]]),
            }
        )
    commands.append(
        {"icon": "i-plus", "text": "New Ticket", "hint": "", "sheet": reverse("console:new-ticket")}
    )
    for r in rows[:COMMAND_TICKETS]:
        commands.append(
            {"icon": "i-doc", "text": f"Open · {r['title']}", "hint": r["id"][:8], "href": r["id"]}
        )
    return {
        "island": upcoming[0] if upcoming else None,
        "island_more": upcoming[1:4],
        "counts": {key: len(by_key.get(key, [])) for key in ("today", "overdue", "triage")},
        "commands": commands,
        "commands_capped": len(rows) > COMMAND_TICKETS,
        "command_tickets": COMMAND_TICKETS,
    }


def report_cards(ticket: dict, now: datetime) -> list[dict]:
    """The three report cards on the ticket page."""
    nxt = next_report(ticket)
    cards = []
    for r in REPORTS:
        ob = ticket["obligations"][r]
        cls, icon, label = STATUS[ob["status"]]
        # The bar needs the window's start. The API gives it for the early warning and
        # notification (aware_at); the final report's start isn't returned, so it has no bar.
        start, since = ticket.get("aware_at"), "awareness"
        window = None
        if r != "final_report" and ob["due_at"] and start and ob["submitted_at"] is None:
            total = (parse_timestamp(ob["due_at"]) - parse_timestamp(start)).total_seconds()
            if total > 0:
                left = (parse_timestamp(ob["due_at"]) - now).total_seconds()
                window = {
                    "start": start,
                    "due": ob["due_at"],
                    "total": span(total),
                    "since": since,
                    "pct": max(0, min(100, round(100 * left / total))),
                    "late": left < 0,
                    "soon": 0 <= left < 12 * 3600,
                    "left": relative(left).removeprefix("in "),
                }
        cards.append(
            {
                "type": r,
                "label": REPORT_LABEL[r],
                "title": REPORT_TITLE[r],
                "due_at": ob["due_at"],
                "status": ob["status"],
                "cls": cls,
                "icon": icon,
                "badge": label,
                "due": utc(ob["due_at"]),
                "submitted": utc(ob["submitted_at"]),
                "reference": ob["reference"],
                "active": r == nxt,
                "window": window if r == nxt else None,
                "count": hms((parse_timestamp(ob["due_at"]) - now).total_seconds(), two=True)
                if r == nxt
                else "",
                "late": r == nxt and parse_timestamp(ob["due_at"]) < now,
                "view": "View Report" if ob["submitted_at"] else "View Draft",
            }
        )
    return cards


def _value(value) -> str:
    if value is None or value == "" or value == []:
        return "none"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k} {_value(v)}" for k, v in value.items())
    return str(value)


def audit(entries: list[dict]) -> list[dict]:
    """The audit trail, newest first, as the prototype shows it."""
    out = []
    for e in reversed(entries):
        changes = {c["field"]: c for c in e.get("changes") or []}
        title, diff, node = e["action"].replace("_", " ").capitalize(), [], ""
        if e["action"] == "triaged":
            state = (changes.get("state") or {}).get("new")
            resolution = (changes.get("resolution") or {}).get("new")
            if state == "reportable":
                title = "Triaged as actively exploited"
            elif resolution in RESOLUTION_LABEL:
                title = "Triaged as " + RESOLUTION_LABEL[resolution].lower()
        elif e["action"] == "report_submitted":
            node = "sub"
            report = next(
                (f.split(".")[1] for f in changes if f.startswith("reports.")),
                None,
            )
            title = REPORT_LABEL.get(report, "Report") + " submitted"
            whole = (changes.get(f"reports.{report}") or {}).get("new")
            ref = whole.get("reference") if isinstance(whole, dict) else None
            if ref:
                diff.append({"text": f"Reference {ref}"})
        elif e["action"] == "updated":
            for c in e.get("changes") or []:
                diff.append({"field": c["field"], "old": _value(c["old"]), "new": _value(c["new"])})
        out.append(
            {
                "title": title,
                "actor": e["actor"],
                "at": utc(e["at"]),
                "action": e["action"],
                "icon": AUDIT_ICON.get(e["action"], "i-doc"),
                "node": node,
                "diff": diff,
                "reason": e.get("reason"),
            }
        )
    return out
