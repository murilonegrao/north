// Types for API contract v0.2 (docs/api/programs-v0.md, including "Changes in v0.1" and "in v0.2"). Field names follow the contract exactly.

export const VERIFICATION_STATUSES = [
  'confirmed_official',
  'reported_by_program',
  'extracted_unverified',
  'unknown',
  'confirmed_negative',
] as const

export type VerificationStatus = (typeof VERIFICATION_STATUSES)[number]

export type SourceKind = 'page' | 'official_list' | 'correspondence' | 'uploaded_file'

/** BR-02: `unknown` has `value: null` and may have no source. */
export interface VerifiedValue<T> {
  value: T | null
  status: VerificationStatus
  source_kind?: SourceKind | null
  source_url?: string | null
  evidence?: string | null
  verified_at?: string | null
}

export interface Money {
  amount: number
  currency: string
}

export const CIP_FAMILIES = ['11', '30.70', '30.71', '52.12'] as const
export type CipFamily = (typeof CIP_FAMILIES)[number]

export const STEM_FILTERS = ['eligible', 'not_eligible', 'unknown'] as const
export type StemFilter = (typeof STEM_FILTERS)[number]

export type ProgramFlag = 'no_stem_opt_extension'

export interface Cip {
  code: string
  title: string
  family: string
  isced_f?: string | null
}

/** Value of `stem_opt` (v0.1 §2). The whole field is `null`-valued when the status is `unknown`. */
export interface StemOptValue {
  eligible: boolean
  rule_version?: string | null
  claim_mismatch?: boolean
}

export type StemOpt = VerifiedValue<StemOptValue>

/** Value of `completions` (v0.1 §1). */
export interface CompletionsValue {
  total: number
  nonresident: number | null
  year: string
}

export type Completions = VerifiedValue<CompletionsValue>

/** IPEDS CONTROL 1/2/3 (v0.1 §7). */
export const INSTITUTION_CONTROLS = ['public', 'private_nonprofit', 'private_for_profit'] as const
export type InstitutionControl = (typeof INSTITUTION_CONTROLS)[number]

export interface InstitutionSummary {
  id: string
  name: string
  /** null when the official file does not say (shown as unknown, never as a type). */
  control: InstitutionControl | null
}

export interface CampusSummary {
  /** null when unknown: the UI shows the state alone. */
  city: string | null
  state: string
}

/** Codes the UI translates (v0.1 §4: no UI text in data). */
export type NoteCode = 'institution_wide_average'

export type TuitionValue = VerifiedValue<Money> & { note_code?: NoteCode | null }

export interface ProgramSummary {
  id: string
  title: string
  title_source: 'cip_title' | 'program_page'
  degree: string
  cip: Cip
  institution: InstitutionSummary
  campus: CampusSummary
  stem_opt: StemOpt
  flags: ProgramFlag[]
  completions: Completions
  /** v0.2 §1: the detail's VerifiedValue without `evidence`. */
  graduate_tuition_nonresident: TuitionValue
  sevp_status: VerificationStatus
  accreditation_status: VerificationStatus
}

export interface ProgramList {
  total: number
  limit: number
  offset: number
  items: ProgramSummary[]
}

export interface Accreditation {
  accreditor: string
  scheme: string
  institutional: boolean
}

export interface IntlAuthorization {
  scheme: string
  authorized: boolean
}

export interface InstitutionDetail extends InstitutionSummary {
  website?: string | null
  identifiers: Record<string, string>
  accreditation: VerifiedValue<Accreditation>
  carnegie_classification: VerifiedValue<string>
}

export interface Locality {
  country: string
  scheme: string
  code: string
  name: string
}

export interface CampusDetail extends CampusSummary {
  locality?: Locality | null
  sevp_campus_code?: string | null
  intl_authorization: VerifiedValue<IntlAuthorization>
}

/** Fixed source ids (v0.1 §5). */
export const SOURCE_IDS = [
  'ipeds_hd',
  'ipeds_c_a',
  'ipeds_ic_ay',
  'dhs_stem_list',
  'sevp_csl',
  'dapip',
  'scorecard_fos',
  'hud_fmr',
] as const
export type SourceId = (typeof SOURCE_IDS)[number]

/** Same shape in `GET /api/sources` and in the detail's `sources[]` (v0.1 §6). */
export interface SourceFile {
  source: SourceId
  file_version: string
  sha256: string
  uploaded_at: string
  /** null when the ingestion run did not record a row count. */
  rows: number | null
}

export interface ProgramDetail extends Omit<ProgramSummary, 'institution' | 'campus' | 'sevp_status' | 'accreditation_status'> {
  institution: InstitutionDetail
  campus: CampusDetail
  graduate_tuition_nonresident: TuitionValue
  not_yet_collected: string[]
  sources: SourceFile[]
}

export const SEVP_FILTERS = ['confirmed', 'unknown'] as const
export type SevpFilter = (typeof SEVP_FILTERS)[number]

export const ACCREDITED_FILTERS = ['true', 'unknown'] as const
export type AccreditedFilter = (typeof ACCREDITED_FILTERS)[number]

export const GRADUATES_FILTERS = ['true', 'false'] as const
export type GraduatesFilter = (typeof GRADUATES_FILTERS)[number]

/** v0.2 §2: sort keys. Unknown values always sort last, in both orders. */
export const SORT_KEYS = ['title', 'institution', 'city', 'tuition', 'graduates', 'nonresident_graduates', 'nonresident_share'] as const
export type SortKey = (typeof SORT_KEYS)[number]
export type SortOrder = 'asc' | 'desc'

export interface ProgramQuery {
  state?: string
  cip_family?: CipFamily[]
  stem?: StemFilter
  q?: string
  control?: InstitutionControl[]
  city?: string[]
  min_tuition?: number
  max_tuition?: number
  sevp?: SevpFilter
  accredited?: AccreditedFilter
  has_graduates?: GraduatesFilter
  sort?: SortKey
  order?: SortOrder
  limit?: number
  offset?: number
}

/** `GET /api/facets` (v0.2 §3): counts for the current state, other filters ignored. */
export interface StateCount {
  state: string
  name: string
  count: number
}

export interface Facets {
  /** null: the whole country (v0.3); cities are then empty. */
  state: string | null
  states: StateCount[]
  total: number
  cip_family: Partial<Record<CipFamily, number>>
  control: Partial<Record<InstitutionControl, number>>
  cities: Array<{ city: string; count: number }>
  stem: Partial<Record<StemFilter, number>>
  sevp: Partial<Record<SevpFilter, number>>
  accredited: Partial<Record<AccreditedFilter, number>>
  has_graduates: Partial<Record<GraduatesFilter, number>>
  tuition: { min: number | null; max: number | null; known: number; unknown: number; currency: string }
}
