// A tiny in-memory implementation of API contract v0.4 over the fictitious fixtures.
// Used by the Vite dev middleware (`npm run dev:mock`) and by the tests.
import type { CourseSummary, ProgramSummary } from '../src/api/types.ts'
import { FIXTURE_COURSE_DETAILS, FIXTURE_COURSES, FIXTURE_DETAILS, FIXTURE_PROGRAMS, FIXTURE_SOURCES } from './fixtures.ts'

export interface MockResponse {
  status: number
  body: unknown
}

const CIP_FAMILIES = ['11', '30.70', '30.71', '52.12'] as const
const STEM = ['eligible', 'not_eligible', 'unknown'] as const
const CONTROLS = ['public', 'private_nonprofit', 'private_for_profit'] as const
const SEVP = ['confirmed', 'unknown'] as const
const ACCREDITED = ['true', 'unknown'] as const
const GRADUATES = ['true', 'false'] as const
const SORTS = ['title', 'institution', 'city', 'tuition', 'graduates', 'nonresident_graduates', 'nonresident_share'] as const
const KINDS = ['degree', 'language_course'] as const
const EXAMS = ['ielts', 'cambridge', 'trinity', 'languagecert', 'toefl', 'pte', 'duolingo', 'tie', 'other'] as const
const BANDS = ['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'] as const
const COUNTRIES = ['US', 'IE'] as const

function invalid(loc: string, msg: string): MockResponse {
  return { status: 422, body: { detail: [{ loc: ['query', loc], msg, type: 'value_error' }] } }
}

const has = (values: readonly string[], v: string | null) => v === null || values.includes(v)

// The same predicates as the backend (north/api/programs.py), so mock facets match mock filters.
function stemOf(item: ProgramSummary): string {
  const s = item.stem_opt
  return s.status === 'unknown' || !s.value ? 'unknown' : s.value.eligible ? 'eligible' : 'not_eligible'
}
function tuitionOf(item: ProgramSummary): number | null {
  const t = item.graduate_tuition_nonresident
  return t.status === 'unknown' || !t.value ? null : t.value.amount
}
function completionsOf(item: ProgramSummary, field: 'total' | 'nonresident'): number | null {
  const c = item.completions
  return c.status === 'unknown' || !c.value ? null : c.value[field]
}
function shareOf(item: ProgramSummary): number | null {
  const total = completionsOf(item, 'total')
  const nonresident = completionsOf(item, 'nonresident')
  return total && nonresident !== null ? nonresident / total : null
}
const sevpMatches = (item: ProgramSummary, v: string) => (v === 'confirmed' ? item.sevp_status === 'confirmed_official' : item.sevp_status === 'unknown')
const accreditedMatches = (item: ProgramSummary, v: string) =>
  v === 'true' ? item.accreditation_status === 'confirmed_official' : item.accreditation_status === 'unknown'
function graduatesMatch(item: ProgramSummary, v: string): boolean {
  const total = completionsOf(item, 'total')
  return total !== null && (v === 'true' ? total > 0 : total === 0)
}

const collator = new Intl.Collator('en', { sensitivity: 'base' })

function sortKey(item: ProgramSummary, key: string): string | number | null {
  switch (key) {
    case 'institution':
      return item.institution.name
    case 'city':
      return item.campus.city
    case 'tuition':
      return tuitionOf(item)
    case 'graduates':
      return completionsOf(item, 'total')
    case 'nonresident_graduates':
      return completionsOf(item, 'nonresident')
    case 'nonresident_share':
      return shareOf(item)
    default:
      return item.title
  }
}

/** v0.2 §2: unknown last in both orders; ties by institution name, then program id. */
function sortItems(items: ProgramSummary[], key: string, order: string): ProgramSummary[] {
  const dir = order === 'desc' ? -1 : 1
  const cmp = (a: string | number, b: string | number) => (typeof a === 'number' && typeof b === 'number' ? a - b : collator.compare(String(a), String(b)))
  return [...items].sort((a, b) => {
    const ka = sortKey(a, key)
    const kb = sortKey(b, key)
    if (ka === null && kb !== null) return 1
    if (kb === null && ka !== null) return -1
    if (ka !== null && kb !== null) {
      const c = cmp(ka, kb) * dir
      if (c !== 0) return c
    }
    if (key !== 'institution') {
      const c = collator.compare(a.institution.name, b.institution.name)
      if (c !== 0) return c
    }
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0
  })
}

function money(raw: string | null): number | undefined | null {
  if (raw === null) return undefined
  const n = Number(raw)
  return raw.trim() !== '' && Number.isFinite(n) && n >= 0 && n <= 1_000_000 ? n : null
}

const STATE_NAMES: Record<string, string> = { TX: 'Texas' }

/** Zero counts of the course groups, for a degree-only scope (v0.4). */
function emptyCourseFacets(degrees: number) {
  return {
    kind: { degree: degrees, language_course: 0 },
    exam: Object.fromEntries([...EXAMS, 'unknown'].map((e) => [e, 0])),
    cefr_entry: Object.fromEntries([...BANDS, 'unknown'].map((b) => [b, 0])),
    hours_per_week: { min: null, max: null, known: 0, unknown: 0 },
  }
}

const COUNTY_NAMES: Record<string, string> = { D: 'Dublin', CO: 'Cork', G: 'Galway', LK: 'Limerick' }
const courseValue = <K extends keyof CourseSummary['language_course']>(c: CourseSummary, key: K) => {
  const v = c.language_course[key] as { value: unknown; status: string }
  return v.status === 'unknown' ? null : v.value
}

/** The same predicates as north/api/programs.py for language courses. */
function courseFacets(state: string | null) {
  const items = FIXTURE_COURSES.filter((c) => state === null || c.campus.state === state)
  const count = (match: (c: CourseSummary) => boolean) => items.filter(match).length
  const cities = new Map<string, number>()
  for (const c of items) if (c.campus.city) cities.set(c.campus.city, (cities.get(c.campus.city) ?? 0) + 1)
  const perCounty = new Map<string, number>()
  for (const c of FIXTURE_COURSES) if (c.campus.state) perCounty.set(c.campus.state, (perCounty.get(c.campus.state) ?? 0) + 1)
  const hours = items.map((c) => courseValue(c, 'hours_per_week') as number | null).filter((n): n is number => n !== null)
  return {
    country: 'IE',
    state,
    kind_scope: 'language_course',
    total: items.length,
    states: [...perCounty]
      .map(([code, n]) => ({ state: code, name: COUNTY_NAMES[code] ?? code, count: n }))
      .sort((a, b) => collator.compare(a.name, b.name)),
    cip_family: {},
    control: Object.fromEntries(CONTROLS.map((c) => [c, 0])),
    cities: [...cities].map(([city, n]) => ({ city, count: n })).sort((a, b) => b.count - a.count || collator.compare(a.city, b.city)),
    stem: { eligible: 0, not_eligible: 0, unknown: items.length },
    sevp: { confirmed: 0, unknown: items.length },
    accredited: { true: 0, unknown: items.length },
    has_graduates: { true: 0, false: 0 },
    tuition: { min: null, max: null, known: 0, unknown: items.length, currency: 'EUR' },
    kind: { degree: 0, language_course: items.length },
    exam: Object.fromEntries([...EXAMS, 'unknown'].map((e) => [e, count((c) => (courseValue(c, 'exam') ?? 'unknown') === e)])),
    cefr_entry: Object.fromEntries([...BANDS, 'unknown'].map((b) => [b, count((c) => (courseValue(c, 'cefr_entry') ?? 'unknown') === b)])),
    hours_per_week: {
      min: hours.length ? Math.min(...hours) : null,
      max: hours.length ? Math.max(...hours) : null,
      known: hours.length,
      unknown: items.length - hours.length,
    },
  }
}

function listCourses(p: URLSearchParams): MockResponse {
  const state = p.get('state')?.toUpperCase() ?? null
  const cities = p.getAll('city')
  const exams = p.getAll('exam')
  if (exams.some((e) => !has(EXAMS, e))) return invalid('exam', 'invalid exam')
  const max = p.get('cefr_entry_max')
  if (!has(BANDS, max)) return invalid('cefr_entry_max', 'invalid band')
  const hoursRaw = p.get('hours_min')
  const hoursMin = hoursRaw === null ? undefined : Number(hoursRaw)
  if (hoursMin !== undefined && (!Number.isFinite(hoursMin) || hoursMin < 0 || hoursMin > 80)) return invalid('hours_min', 'must be 0..80')
  const limit = Number(p.get('limit') ?? 50)
  const offset = Number(p.get('offset') ?? 0)
  const allowed = max ? BANDS.slice(0, BANDS.indexOf(max as (typeof BANDS)[number]) + 1) : null
  const matches = FIXTURE_COURSES.filter((c) => {
    if (state !== null && c.campus.state !== state) return false
    if (cities.length && (c.campus.city === null || !cities.includes(c.campus.city))) return false
    const exam = courseValue(c, 'exam') as string | null
    if (exams.length && (exam === null || !exams.includes(exam))) return false
    const entry = courseValue(c, 'cefr_entry') as (typeof BANDS)[number] | null
    if (allowed && entry !== null && !allowed.includes(entry)) return false // unknown entry kept (BR-02)
    const hours = courseValue(c, 'hours_per_week') as number | null
    if (hoursMin !== undefined && (hours === null || hours < hoursMin)) return false
    return true
  }).sort((a, b) => collator.compare(a.title, b.title) || collator.compare(a.institution.name, b.institution.name))
  return { status: 200, body: { total: matches.length, limit, offset, items: matches.slice(offset, offset + limit) } }
}

function facets(state: string | null) {
  const items = FIXTURE_PROGRAMS.filter((item) => state === null || item.campus.state === state)
  const perState = new Map<string, number>()
  for (const item of FIXTURE_PROGRAMS) perState.set(item.campus.state, (perState.get(item.campus.state) ?? 0) + 1)
  const countBy = <T extends string>(values: readonly T[], match: (item: ProgramSummary, v: T) => boolean) =>
    Object.fromEntries(values.map((v) => [v, items.filter((item) => match(item, v)).length]))
  const cities = new Map<string, number>()
  if (state !== null) for (const item of items) if (item.campus.city) cities.set(item.campus.city, (cities.get(item.campus.city) ?? 0) + 1)
  const amounts = items.map(tuitionOf).filter((n): n is number => n !== null)
  return {
    state,
    total: items.length,
    states: [...perState]
      .map(([code, count]) => ({ state: code, name: STATE_NAMES[code] ?? code, count }))
      .sort((a, b) => collator.compare(a.name, b.name)),
    cip_family: countBy(CIP_FAMILIES, (item, f) => item.cip.family === f),
    control: countBy(CONTROLS, (item, c) => item.institution.control === c),
    cities: [...cities]
      .map(([city, count]) => ({ city, count }))
      .sort((a, b) => b.count - a.count || collator.compare(a.city, b.city)),
    stem: countBy(STEM, (item, v) => stemOf(item) === v),
    sevp: countBy(SEVP, sevpMatches),
    accredited: countBy(ACCREDITED, accreditedMatches),
    has_graduates: countBy(GRADUATES, graduatesMatch),
    country: 'US',
    kind_scope: null,
    ...emptyCourseFacets(items.length),
    tuition: {
      min: amounts.length ? Math.min(...amounts) : null,
      max: amounts.length ? Math.max(...amounts) : null,
      known: amounts.length,
      unknown: items.length - amounts.length,
      currency: 'USD',
    },
  }
}

export function handleMockRequest(rawUrl: string): MockResponse | null {
  const url = new URL(rawUrl, 'http://mock.local')
  const path = url.pathname.replace(/\/+$/, '')
  const p = url.searchParams

  if (path === '/api/health') return { status: 200, body: { status: 'ok', version: 'mock' } }
  if (path === '/api/sources') {
    return { status: 200, body: FIXTURE_SOURCES }
  }

  if (path === '/api/facets') {
    const state = p.get('state')
    if (state !== null && !/^[A-Za-z]{1,3}$/.test(state)) return invalid('state', 'invalid state')
    const country = p.get('country')?.toUpperCase() ?? null
    if (country !== null && !has(COUNTRIES, country)) return invalid('country', 'unknown country')
    if (!has(KINDS, p.get('kind'))) return invalid('kind', 'invalid kind')
    if (country === 'IE') return { status: 200, body: courseFacets(state ? state.toUpperCase() : null) }
    return { status: 200, body: facets(state ? state.toUpperCase() : null) }
  }

  if (path === '/api/programs') {
    const country = p.get('country')?.toUpperCase() ?? null
    if (country !== null && !has(COUNTRIES, country)) return invalid('country', 'unknown country')
    const kind = p.get('kind')
    if (!has(KINDS, kind)) return invalid('kind', 'invalid kind')
    if (country === 'IE') {
      if (kind === 'degree') return { status: 200, body: { total: 0, limit: Number(p.get('limit') ?? 50), offset: 0, items: [] } }
      return listCourses(p)
    }
    if (kind === 'language_course') return { status: 200, body: { total: 0, limit: Number(p.get('limit') ?? 50), offset: 0, items: [] } }
    const state = p.get('state')?.toUpperCase() ?? null
    const families = p.getAll('cip_family')
    if (families.some((f) => !has(CIP_FAMILIES, f))) return invalid('cip_family', 'invalid CIP family')
    const stem = p.get('stem')
    if (!has(STEM, stem)) return invalid('stem', 'invalid STEM filter')
    const controls = p.getAll('control')
    if (controls.some((c) => !has(CONTROLS, c))) return invalid('control', 'invalid control')
    const cities = p.getAll('city')
    if (cities.length > 50 || cities.some((c) => c.length < 1 || c.length > 120)) return invalid('city', 'invalid city')
    const sevp = p.get('sevp')
    if (!has(SEVP, sevp)) return invalid('sevp', 'invalid SEVP filter')
    const accredited = p.get('accredited')
    if (!has(ACCREDITED, accredited)) return invalid('accredited', 'invalid accreditation filter')
    const graduates = p.get('has_graduates')
    if (!has(GRADUATES, graduates)) return invalid('has_graduates', 'invalid graduates filter')
    const minTuition = money(p.get('min_tuition'))
    const maxTuition = money(p.get('max_tuition'))
    if (minTuition === null) return invalid('min_tuition', 'must be a number >= 0')
    if (maxTuition === null) return invalid('max_tuition', 'must be a number >= 0')
    if (minTuition !== undefined && maxTuition !== undefined && maxTuition < minTuition) {
      return invalid('max_tuition', 'max_tuition must be greater than or equal to min_tuition')
    }
    const sort = p.get('sort') ?? 'title'
    if (!has(SORTS, sort)) return invalid('sort', 'invalid sort')
    const order = p.get('order') ?? 'asc'
    if (order !== 'asc' && order !== 'desc') return invalid('order', 'invalid order')
    const limit = Number(p.get('limit') ?? 50)
    const offset = Number(p.get('offset') ?? 0)
    if (!Number.isInteger(limit) || limit < 1 || limit > 200) return invalid('limit', 'limit must be 1..200')
    if (!Number.isInteger(offset) || offset < 0) return invalid('offset', 'offset must be >= 0')
    const q = (p.get('q') ?? '').trim().toLowerCase()

    const matches = FIXTURE_PROGRAMS.filter((item) => {
      if (state !== null && item.campus.state !== state) return false
      if (families.length && !families.includes(item.cip.family)) return false
      // v0.1 §8: unknown = status unknown, whatever else is true; otherwise value.eligible decides.
      if (stem && stemOf(item) !== stem) return false
      if (q) {
        const haystack = `${item.institution.name} ${item.campus.city ?? ''} ${item.cip.title} ${item.title}`.toLowerCase()
        if (!haystack.includes(q)) return false
      }
      if (controls.length && (item.institution.control === null || !controls.includes(item.institution.control))) return false
      if (cities.length && (item.campus.city === null || !cities.includes(item.campus.city))) return false
      if (minTuition !== undefined || maxTuition !== undefined) {
        const amount = tuitionOf(item)
        if (amount === null) return false // v0.2: unknown tuition is excluded when a bound is set
        if (minTuition !== undefined && amount < minTuition) return false
        if (maxTuition !== undefined && amount > maxTuition) return false
      }
      if (sevp && !sevpMatches(item, sevp)) return false
      if (accredited && !accreditedMatches(item, accredited)) return false
      if (graduates && !graduatesMatch(item, graduates)) return false
      return true
    })
    const sorted = sortItems(matches, sort, order)
    return { status: 200, body: { total: sorted.length, limit, offset, items: sorted.slice(offset, offset + limit) } }
  }

  const detail = path.match(/^\/api\/programs\/([^/]+)$/)
  if (detail) {
    const id = decodeURIComponent(detail[1]!)
    const program = FIXTURE_DETAILS[id] ?? FIXTURE_COURSE_DETAILS[id]
    return program ? { status: 200, body: program } : { status: 404, body: { detail: 'program not found' } }
  }

  if (path.startsWith('/api/')) return { status: 404, body: { detail: 'Not Found' } }
  return null
}
