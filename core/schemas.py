"""Ticket input schemas from the common OpenAPI contract."""

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from cra_service.timestamps import Timestamp
from cra_service.validation import RequestSchema

ShortText = Annotated[str, Field(strict=True, min_length=1, max_length=200)]
LongText = Annotated[str, Field(strict=True, min_length=1, max_length=10000)]
Version = Annotated[str, Field(strict=True, min_length=1, max_length=100)]
Versions = Annotated[list[Version], Field(max_length=50)]
ReporterText = Annotated[str, Field(strict=True, max_length=200)]
MemberState = Literal[
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
]
Severity = Literal["low", "medium", "high", "critical"]
Sensitivity = Literal["CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED"]


class ProductIn(RequestSchema):
    manufacturer: ShortText
    name: ShortText
    affected_versions: Versions = Field(default=None)


class ProductPatch(RequestSchema):
    manufacturer: ShortText = Field(default=None)
    name: ShortText = Field(default=None)
    affected_versions: Versions | None = None


class ReporterIn(RequestSchema):
    name: ReporterText = Field(default=None)
    contact: ReporterText = Field(default=None)


class VulnerabilityIn(RequestSchema):
    cve_id: Annotated[str, Field(strict=True, pattern=r"^CVE-\d{4}-\d{4,}$")] = Field(default=None)
    description: LongText = Field(default=None)


class ExploitIn(RequestSchema):
    description: LongText = Field(default=None)


class MitigationsIn(RequestSchema):
    taken: LongText = Field(default=None)
    for_users: LongText = Field(default=None)


class FixIn(RequestSchema):
    available_at: Timestamp = Field(default=None)
    description: LongText = Field(default=None)
    fixed_versions: Versions = Field(default=None)


class _MemberStates(RequestSchema):
    @field_validator("member_states", check_fields=False)
    @classmethod
    def unique_member_states(cls, value):
        if value is not None and len(set(value)) != len(value):
            raise ValueError("must contain unique member states")
        return value


class TicketCreate(_MemberStates):
    source: Literal["external_researcher", "customer", "internal", "scanner", "csirt"]
    title: ShortText
    description: LongText
    product: ProductIn
    reporter: ReporterIn = Field(default=None)
    member_states: list[MemberState] = Field(default=None)
    vulnerability: VulnerabilityIn = Field(default=None)
    exploit: ExploitIn = Field(default=None)
    mitigations: MitigationsIn = Field(default=None)
    impact: LongText = Field(default=None)
    malicious_actor: LongText = Field(default=None)
    sensitivity: Sensitivity = Field(default=None)
    severity: Severity = Field(default=None)
    fix: FixIn = Field(default=None)


class TicketUpdate(_MemberStates):
    title: ShortText = Field(default=None)
    description: LongText = Field(default=None)
    product: ProductPatch = Field(default=None)
    reporter: ReporterIn | None = None
    member_states: list[MemberState] | None = None
    vulnerability: VulnerabilityIn | None = None
    exploit: ExploitIn | None = None
    mitigations: MitigationsIn | None = None
    impact: LongText | None = None
    malicious_actor: LongText | None = None
    sensitivity: Sensitivity | None = None
    severity: Severity | None = None
    fix: FixIn | None = None
    aware_at: Timestamp = Field(default=None)
    change_reason: LongText = Field(default=None)

    @model_validator(mode="after")
    def nonempty_update(self):
        if not self.model_fields_set:
            raise ValueError("must contain at least one update field")
        return self


class TriageRequest(RequestSchema):
    decision: Literal["actively_exploited", "not_actively_exploited", "invalid"]
    reason: LongText
    aware_at: Timestamp = Field(default=None)
