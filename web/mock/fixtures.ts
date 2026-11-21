// FICTITIOUS fixture data for `npm run dev:mock` and the tests. Every institution, city,
// identifier and number here is invented; none of it describes a real program.
// Shapes follow docs/api/programs-v0.md (contract v0.2) exactly.
import type {
  Accreditation,
  CipFamily,
  Completions,
  InstitutionControl,
  ProgramDetail,
  ProgramSummary,
  SourceFile,
  StemOpt,
  TuitionValue,
  VerificationStatus,
  VerifiedValue,
} from '../src/api/types.ts'

const FILE_URL = 'https://example.org/fictitious-official-file'
const LIST_URL = 'https://example.org/fictitious-stem-list.pdf'
const VERIFIED_AT = '2026-11-21'

interface FakeInstitution {
  unitid: string
  name: string
  city: string
  control: InstitutionControl
  sevp: VerificationStatus
  accreditation: VerificationStatus
  tuition: number | null
}

const INSTITUTIONS: FakeInstitution[] = [
  { unitid: '990001', name: 'Example State University', city: 'Example City', control: 'public', sevp: 'confirmed_official', accreditation: 'confirmed_official', tuition: 21480 },
  { unitid: '990002', name: 'Sample Institute of Technology', city: 'Sampleton', control: 'private_nonprofit', sevp: 'confirmed_official', accreditation: 'confirmed_official', tuition: 48900 },
  { unitid: '990003', name: 'Placeholder University at Lakeview', city: 'Lakeview Example', control: 'public', sevp: 'unknown', accreditation: 'confirmed_official', tuition: 18320 },
  { unitid: '990004', name: 'Fictional Plains College', city: 'Mocksville', control: 'private_nonprofit', sevp: 'confirmed_negative', accreditation: 'extracted_unverified', tuition: null },
  { unitid: '990005', name: 'Demo Coastal University', city: 'Port Example', control: 'public', sevp: 'confirmed_official', accreditation: 'reported_by_program', tuition: 23950 },
  { unitid: '990006', name: 'Example Hill Seminary of Data', city: 'Testburg', control: 'private_nonprofit', sevp: 'reported_by_program', accreditation: 'unknown', tuition: 36100 },
  { unitid: '990007', name: 'Mockup Career Institute', city: 'Example City', control: 'private_for_profit', sevp: 'unknown', accreditation: 'unknown', tuition: 14250 },
]

interface FakeCip {
  code: string
  title: string
  family: CipFamily
  isced: string
  stem: 'eligible' | 'not_eligible' | 'unknown'
}

const CIPS: FakeCip[] = [
  { code: '11.0701', title: 'Computer Science.', family: '11', isced: '0613', stem: 'eligible' },
  { code: '11.0401', title: 'Information Science/Studies.', family: '11', isced: '0612', stem: 'eligible' },
  { code: '11.1003', title: 'Computer and Information Systems Security/Auditing/Information Assurance.', family: '11', isced: '0612', stem: 'eligible' },
  { code: '30.7001', title: 'Data Science, General.', family: '30.70', isced: '0588', stem: 'eligible' },
  { code: '30.7101', title: 'Data Analytics, General.', family: '30.71', isced: '0588', stem: 'unknown' },
  { code: '52.1201', title: 'Management Information Systems, General.', family: '52.12', isced: '0413', stem: 'not_eligible' },
]

// Which (institution, CIP) pairs exist, as indexes into CIPS.
const OFFERINGS: number[][] = [
  [0, 1, 2, 3, 4, 5],
  [0, 2, 3, 4, 5],
  [0, 1, 3, 5],
  [0, 4, 5],
  [0, 1, 2, 3, 4, 5],
  [3, 4, 5],
  [0, 4],
]

function cipTitle(title: string): string {
  return title.replace(/\.$/, '')
}

function stemOpt(cip: FakeCip, withEvidence: boolean): StemOpt {
  if (cip.stem === 'unknown') return { value: null, status: 'unknown' }
  return {
    value: { eligible: cip.stem === 'eligible', rule_version: '2024-07-22', claim_mismatch: false },
    status: cip.stem === 'eligible' ? 'confirmed_official' : 'confirmed_negative',
    source_kind: 'official_list',
    source_url: LIST_URL,
    ...(withEvidence ? { evidence: `CIP ${cip.code} (fictitious list row)` } : {}),
    verified_at: VERIFIED_AT,
  }
}

function completions(seed: number, withEvidence: boolean): Completions {
  if (seed % 7 === 3) return { value: null, status: 'unknown' }
  const total = seed % 11 === 5 ? 0 : 18 + ((seed * 37) % 290)
  // Some rows have a total but no nonresident count: that part is unknown, never 0.
  const nonresident = seed % 9 === 4 ? null : Math.round(total * (0.35 + ((seed * 13) % 50) / 100))
  return {
    value: { total, nonresident, year: '2023-24' },
    status: 'confirmed_official',
    source_kind: 'uploaded_file',
    source_url: FILE_URL,
    ...(withEvidence ? { evidence: 'C2024_A FICTITIOUS ROW 7' } : {}),
    verified_at: VERIFIED_AT,
  }
}

/** Institution-wide average (v0.2 §1); the list omits `evidence`. */
function tuition(inst: FakeInstitution, withEvidence: boolean): TuitionValue {
  if (inst.tuition === null) return { value: null, status: 'unknown', note_code: 'institution_wide_average' }
  return {
    value: { amount: inst.tuition, currency: 'USD' },
    status: 'confirmed_official',
    source_kind: 'uploaded_file',
    source_url: FILE_URL,
    ...(withEvidence ? { evidence: 'IC2024_AY FICTITIOUS ROW 42' } : {}),
    verified_at: VERIFIED_AT,
    note_code: 'institution_wide_average',
  }
}

function summary(inst: FakeInstitution, cip: FakeCip, seed: number, detail = false): ProgramSummary {
  return {
    id: `${inst.unitid}-${cip.code.replace('.', '')}`,
    title: seed === 0 ? 'Master of Science in Computer Science' : cipTitle(cip.title),
    title_source: seed === 0 ? 'program_page' : 'cip_title',
    degree: "Master's",
    cip: { code: cip.code, title: cip.title, family: cip.family },
    institution: { id: inst.unitid, name: inst.name, control: inst.control },
    campus: { city: inst.city, state: 'TX' },
    stem_opt: stemOpt(cip, detail),
    flags: cip.family === '52.12' ? ['no_stem_opt_extension'] : [],
    completions: completions(seed, detail),
    graduate_tuition_nonresident: tuition(inst, detail),
    sevp_status: inst.sevp,
    accreditation_status: inst.accreditation,
  }
}

function verified<T>(status: VerificationStatus, value: T | null, extra: Partial<VerifiedValue<T>> = {}): VerifiedValue<T> {
  if (status === 'unknown') return { value: null, status }
  const source: Partial<VerifiedValue<T>> =
    status === 'reported_by_program' || status === 'extracted_unverified'
      ? { source_kind: 'page', source_url: 'https://example.org/fictitious-program-page' }
      : { source_kind: 'uploaded_file', source_url: FILE_URL }
  return {
    value,
    status,
    ...source,
    evidence: status === 'extracted_unverified' ? '"Accredited by the Example Commission" (fictitious excerpt)' : 'FICTITIOUS ROW 42',
    verified_at: VERIFIED_AT,
    ...extra,
  }
}

const sha = (n: number) => n.toString(16).padStart(64, '0')
const SOURCES: SourceFile[] = [
  { source: 'ipeds_hd', file_version: 'HD2024', sha256: sha(1), uploaded_at: '2026-11-21T03:30:00Z', rows: 6 },
  { source: 'ipeds_c_a', file_version: 'C2024_A', sha256: sha(2), uploaded_at: '2026-11-21T03:31:00Z', rows: 27 },
  { source: 'ipeds_ic_ay', file_version: 'IC2024_AY', sha256: sha(3), uploaded_at: '2026-11-21T03:31:30Z', rows: 6 },
  { source: 'dhs_stem_list', file_version: '2024-07-22', sha256: sha(4), uploaded_at: '2026-11-21T03:32:00Z', rows: 5 },
  { source: 'sevp_csl', file_version: '2026-10', sha256: sha(5), uploaded_at: '2026-11-21T03:33:00Z', rows: 4 },
  { source: 'dapip', file_version: '2026-11', sha256: sha(6), uploaded_at: '2026-11-21T03:34:00Z', rows: 6 },
]

function detail(inst: FakeInstitution, cip: FakeCip, seed: number): ProgramDetail {
  const base = summary(inst, cip, seed, true)
  const { sevp_status: _sevp, accreditation_status: _acc, ...rest } = base
  return {
    ...rest,
    cip: { ...base.cip, isced_f: cip.isced },
    institution: {
      ...base.institution,
      website: 'https://example.org/',
      identifiers: { unitid: inst.unitid, opeid: `99${inst.unitid}00` },
      accreditation:
        inst.accreditation === 'confirmed_negative'
          ? verified<Accreditation>(inst.accreditation, null)
          : verified(inst.accreditation, { accreditor: 'Example Accrediting Commission', scheme: 'us_ed_recognized', institutional: true }),
      carnegie_classification: { value: null, status: 'unknown' },
    },
    campus: {
      ...base.campus,
      locality: { country: 'US', scheme: 'us_county_fips', code: '48999', name: 'Example County' },
      sevp_campus_code: null,
      intl_authorization: verified(inst.sevp, { scheme: 'sevp', authorized: inst.sevp !== 'confirmed_negative' }),
    },
    graduate_tuition_nonresident: tuition(inst, true),
    not_yet_collected: [
      'admissions.english',
      'admissions.deadlines',
      'admissions.other_field_accepted',
      'funding',
      'cost.program_tuition',
      'immigration.i20_issued_for_program',
    ],
    sources: SOURCES,
  }
}

const PAIRS: Array<[FakeInstitution, FakeCip, number]> = []
INSTITUTIONS.forEach((inst, i) => {
  for (const c of OFFERINGS[i] ?? []) PAIRS.push([inst, CIPS[c]!, PAIRS.length])
})

export const FIXTURE_PROGRAMS: ProgramSummary[] = PAIRS.map(([inst, cip, seed]) => summary(inst, cip, seed))
export const FIXTURE_DETAILS: Record<string, ProgramDetail> = Object.fromEntries(
  PAIRS.map(([inst, cip, seed]) => {
    const d = detail(inst, cip, seed)
    return [d.id, d]
  }),
)
export const FIXTURE_SOURCES = SOURCES
