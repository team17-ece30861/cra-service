from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from cra_service.timestamps import format_timestamp, parse_timestamp

DraftReportType = Literal["early_warning", "notification", "final_report", "user_advisory"]

_PRODUCT_FIELDS = ("product.manufacturer", "product.name", "product.affected_versions")
_EARLY_WARNING_FIELDS = (*_PRODUCT_FIELDS, "member_states")
_NOTIFICATION_FIELDS = (
    *_EARLY_WARNING_FIELDS,
    "vulnerability.description",
    "exploit.description",
    "mitigations.taken",
    "mitigations.for_users",
    "sensitivity",
)
_REQUIRED_FIELDS = {
    "early_warning": _EARLY_WARNING_FIELDS,
    "notification": _NOTIFICATION_FIELDS,
    "final_report": (
        *_NOTIFICATION_FIELDS,
        "severity",
        "impact",
        "fix.available_at",
        "fix.description",
        "fix.fixed_versions",
    ),
    "user_advisory": (*_PRODUCT_FIELDS, "vulnerability.description", "mitigations.for_users"),
}
_OPTIONAL_FIELDS = {
    "early_warning": (),
    "notification": ("vulnerability.cve_id",),
    "final_report": ("vulnerability.cve_id", "malicious_actor"),
    "user_advisory": (
        "vulnerability.cve_id",
        "severity",
        "impact",
        "fix.available_at",
        "fix.description",
        "fix.fixed_versions",
    ),
}


@dataclass(frozen=True)
class DraftResult:
    content: dict[str, Any]
    missing_fields: list[str]


def _field_value(fields: Mapping[str, Any], field: str) -> Any:
    value = fields
    for part in field.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def build_draft(
    *,
    report_type: DraftReportType,
    ticket_id: str,
    aware_at: datetime,
    ticket_fields: Mapping[str, Any],
) -> DraftResult:
    """Build Model C content from validated ticket fields without reading storage or time.

    The caller checks ticket applicability and handles submitted snapshots. Present,
    nonempty allowed fields retain their nested ticket structure. Required fields
    that are absent, null, empty strings, or empty lists are named with dotted paths.
    Returned content owns its values and never includes reporter or unrelated fields.
    """
    if report_type not in _REQUIRED_FIELDS:
        raise ValueError("unknown report type")

    content = {"ticket_id": ticket_id, "aware_at": format_timestamp(aware_at)}
    missing_fields = []
    required_fields = _REQUIRED_FIELDS[report_type]
    for field in (*required_fields, *_OPTIONAL_FIELDS[report_type]):
        value = _field_value(ticket_fields, field)
        if value is None or value == "" or value == []:
            if field in required_fields:
                missing_fields.append(field)
            continue
        if field == "fix.available_at":
            value = format_timestamp(parse_timestamp(value) if isinstance(value, str) else value)
        if "." in field:
            parent, name = field.split(".")
            content.setdefault(parent, {})[name] = deepcopy(value)
        else:
            content[field] = deepcopy(value)

    return DraftResult(content=content, missing_fields=missing_fields)
