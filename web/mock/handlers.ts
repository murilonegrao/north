// A tiny in-memory implementation of API contract v0.2 over the fictitious fixtures.
// Used by the Vite dev middleware (`npm run dev:mock`) and by the tests.
import type { ProgramSummary } from '../src/api/types.ts'
import { FIXTURE_DETAILS, FIXTURE_PROGRAMS, FIXTURE_SOURCES } from './fixtures.ts'

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
    if (state !== null && !/^[A-Za-z]{2}$/.test(state)) return invalid('state', 'invalid state')
    return { status: 200, body: facets(state ? state.toUpperCase() : null) }
  }

  if (path === '/api/programs') {
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
    const program = FIXTURE_DETAILS[decodeURIComponent(detail[1]!)]
    return program ? { status: 200, body: program } : { status: 404, body: { detail: 'program not found' } }
  }

  if (path.startsWith('/api/')) return { status: 404, body: { detail: 'Not Found' } }
  return null
}
