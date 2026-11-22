"""Response models of API contract v0.4 (docs/api/programs-v0.md)."""

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
    # Null for a language course (there is no institution-wide average to qualify).
    note_code: str | None = "institution_wide_average"


class ListTuitionValue(BaseModel):
    """List items carry the detail's tuition VerifiedValue without ``evidence`` (v0.2 §1)."""
    value: Money | None = None
    status: StatusStr = "unknown"
    source_kind: SourceKindStr | None = None
    source_url: str | None = None
    verified_at: str | None = None
    note_code: str | None = "institution_wide_average"


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


class RuleNote(BaseModel):
    """A migration rule shown next to a value (v0.4), e.g. ``ie.ilep_end``; the UI translates
    ``code`` and may use ``params``."""
    code: str
    params: dict[str, Any]
    source_url: str
    checked_on: str


class ProgramAuthorizationValue(AuthorizationValue):
    """Program-level authorization (record 0008/T5) with the notes of its scheme."""
    notes: list[RuleNote] = []


Kind = Literal["degree", "language_course"]


class LanguageCourse(BaseModel):
    """Course facts (record 0008/T13), each a VerifiedValue. ``cefr_entry``/``cefr_exit`` are
    CEFR bands (A0 = pre-A1), ``exam`` an exam code, ``price`` Money, ``start_dates`` a list."""
    model_config = ConfigDict(extra="allow")
    cefr_entry: VerifiedValue
    cefr_exit: VerifiedValue
    exam: VerifiedValue
    weeks: VerifiedValue
    hours_per_week: VerifiedValue
    price: VerifiedValue
    start_dates: list[VerifiedValue]


class ListVerifiedValue(BaseModel):
    """A VerifiedValue as list items carry it: without ``evidence`` (v0.2 §1, v0.4)."""
    model_config = ConfigDict(extra="allow")
    value: Any = None
    status: StatusStr = "unknown"
    source_kind: SourceKindStr | None = None
    source_url: str | None = None
    verified_at: str | None = None


class ListLanguageCourse(BaseModel):
    cefr_entry: ListVerifiedValue
    cefr_exit: ListVerifiedValue
    exam: ListVerifiedValue
    weeks: ListVerifiedValue
    hours_per_week: ListVerifiedValue
    price: ListVerifiedValue
    start_dates: list[ListVerifiedValue]


class ListProgramAuthorizationValue(ListVerifiedValue):
    value: Authorization | None = None
    notes: list[RuleNote] = []


class ProgramIdentifierRef(BaseModel):
    scheme: str
    value: str


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
    state: str | None  # local subdivision code; null when the files do not place it in one


class ProgramItem(BaseModel):
    id: str
    kind: Kind
    country: str
    title: str
    title_source: Literal["cip_title", "program_page"]
    degree: str
    cip: Cip | None
    institution: InstitutionRef
    campus: CampusRef
    stem_opt: StemOptValue
    flags: list[str]
    completions: CompletionsValue
    graduate_tuition_nonresident: ListTuitionValue
    sevp_status: StatusStr
    accreditation_status: StatusStr
    language_course: ListLanguageCourse | None
    intl_authorization: ListProgramAuthorizationValue | None


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
    kind: Kind
    country: str
    title: str
    title_source: Literal["cip_title", "program_page"]
    degree: str
    cip: CipDetail | None
    identifiers: list[ProgramIdentifierRef]
    institution: InstitutionDetail
    campus: CampusDetail
    stem_opt: StemOptValue
    flags: list[str]
    completions: CompletionsValue
    graduate_tuition_nonresident: TuitionValue
    language_course: LanguageCourse | None
    intl_authorization: ProgramAuthorizationValue | None
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


class StateCount(BaseModel):
    state: str
    name: str
    count: int


class HoursFacet(BaseModel):
    min: float | int | None
    max: float | int | None
    known: int
    unknown: int


class Facets(BaseModel):
    """``GET /api/facets`` (v0.2 §3): counts over every program of ``state``, or of the
    whole country when ``state`` is null (v0.3), and of ``kind_scope`` when given (v0.4).
    ``cities`` is empty without a state unless the country's city names are unique."""
    country: str
    state: str | None
    kind_scope: Kind | None
    total: int
    states: list[StateCount]
    cip_family: dict[str, int]
    control: dict[str, int]
    cities: list[CityCount]
    stem: dict[str, int]
    sevp: dict[str, int]
    accredited: dict[str, int]
    has_graduates: dict[str, int]
    tuition: TuitionFacet
    kind: dict[str, int]
    exam: dict[str, int]
    cefr_entry: dict[str, int]
    hours_per_week: HoursFacet
