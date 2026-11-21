"""Response models of API contract v0.2 (docs/api/programs-v0.md)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

StatusStr = Literal["confirmed_official", "reported_by_program", "extracted_unverified",
                    "unknown", "confirmed_negative"]
SourceKindStr = Literal["page", "official_list", "correspondence", "uploaded_file"]


class VerifiedValue(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: Any = None
    status: StatusStr = "unknown"
    source_kind: SourceKindStr | None = None
    source_url: str | None = None
    evidence: str | None = None
    verified_at: str | None = None


class Completions(BaseModel):
    total: int
    nonresident: int | None
    year: str


class CompletionsValue(VerifiedValue):
    value: Completions | None = None


class StemOpt(BaseModel):
    eligible: bool
    rule_version: str
    claim_mismatch: bool


class StemOptValue(VerifiedValue):
    value: StemOpt | None = None


class Money(BaseModel):
    amount: float | int
    currency: str


class TuitionValue(VerifiedValue):
    value: Money | None = None
    note_code: str = "institution_wide_average"


class ListTuitionValue(BaseModel):
    """List items carry the detail's tuition VerifiedValue without ``evidence`` (v0.2 §1)."""
    value: Money | None = None
    status: StatusStr = "unknown"
    source_kind: SourceKindStr | None = None
    source_url: str | None = None
    verified_at: str | None = None
    note_code: str = "institution_wide_average"


class Accreditation(BaseModel):
    accreditor: str
    scheme: str
    institutional: bool


class AccreditationValue(VerifiedValue):
    value: Accreditation | None = None


class Authorization(BaseModel):
    scheme: str
    authorized: bool


class AuthorizationValue(VerifiedValue):
    value: Authorization | None = None


class Cip(BaseModel):
    code: str
    title: str
    family: str | None


class CipDetail(Cip):
    isced_f: str | None


class InstitutionRef(BaseModel):
    id: str
    name: str
    control: Literal["public", "private_nonprofit", "private_for_profit"] | None


class CampusRef(BaseModel):
    city: str | None
    state: str


class ProgramItem(BaseModel):
    id: str
    title: str
    title_source: Literal["cip_title", "program_page"]
    degree: str
    cip: Cip
    institution: InstitutionRef
    campus: CampusRef
    stem_opt: StemOptValue
    flags: list[str]
    completions: CompletionsValue
    graduate_tuition_nonresident: ListTuitionValue
    sevp_status: StatusStr
    accreditation_status: StatusStr


class ProgramList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ProgramItem]


class InstitutionDetail(InstitutionRef):
    website: str | None
    identifiers: dict[str, str]
    accreditation: AccreditationValue
    carnegie_classification: VerifiedValue


class Locality(BaseModel):
    country: str
    scheme: str
    code: str
    name: str


class CampusDetail(CampusRef):
    locality: Locality | None
    sevp_campus_code: str | None
    intl_authorization: AuthorizationValue


class SourceRef(BaseModel):
    source: str
    file_version: str
    sha256: str
    uploaded_at: str
    rows: int | None


class ProgramDetail(BaseModel):
    id: str
    title: str
    title_source: Literal["cip_title", "program_page"]
    degree: str
    cip: CipDetail
    institution: InstitutionDetail
    campus: CampusDetail
    stem_opt: StemOptValue
    flags: list[str]
    completions: CompletionsValue
    graduate_tuition_nonresident: TuitionValue
    not_yet_collected: list[str]
    sources: list[SourceRef]


class CityCount(BaseModel):
    city: str
    count: int


class TuitionFacet(BaseModel):
    min: float | int | None
    max: float | int | None
    known: int
    unknown: int
    currency: str


class Facets(BaseModel):
    """``GET /api/facets`` (v0.2 §3): counts over every program of ``state``."""
    state: str
    total: int
    cip_family: dict[str, int]
    control: dict[str, int]
    cities: list[CityCount]
    stem: dict[str, int]
    sevp: dict[str, int]
    accredited: dict[str, int]
    has_graduates: dict[str, int]
    tuition: TuitionFacet
