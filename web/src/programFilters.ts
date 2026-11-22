// Program list state <-> URL query (NFR-15: every filter and the sort live in a shareable URL).
// Pure functions, so the mapping is tested without mounting the view.
import type { LocationQuery, LocationQueryRaw } from 'vue-router'
import {
  ACCREDITED_FILTERS,
  type AccreditedFilter,
  CIP_FAMILIES,
  type CipFamily,
  GRADUATES_FILTERS,
  type GraduatesFilter,
  INSTITUTION_CONTROLS,
  type InstitutionControl,
  type ProgramQuery,
  SEVP_FILTERS,
  type SevpFilter,
  SORT_KEYS,
  type SortKey,
  type SortOrder,
  STEM_FILTERS,
  type StemFilter,
} from './api/types'

export interface ProgramFilters {
  state?: string
  q: string
  cip: CipFamily[]
  stem?: StemFilter
  control: InstitutionControl[]
  city: string[]
  minTuition?: number
  maxTuition?: number
  sevp?: SevpFilter
  accredited?: AccreditedFilter
  hasGraduates?: GraduatesFilter
  sort: SortKey
  order: SortOrder
  page: number
}

/** The order a field starts in when the user picks it: cheapest first, most graduates first. */
export const DEFAULT_ORDER: Record<SortKey, SortOrder> = {
  title: 'asc',
  institution: 'asc',
  city: 'asc',
  tuition: 'asc',
  graduates: 'desc',
  nonresident_graduates: 'desc',
  nonresident_share: 'desc',
}

const MAX_CITIES = 50

function asList(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((v): v is string => typeof v === 'string')
  return typeof value === 'string' ? [value] : []
}

function first(query: LocationQuery, key: string): string | undefined {
  return asList(query[key])[0]
}

function oneOf<T extends string>(values: readonly T[], raw: string | undefined): T | undefined {
  return (values as readonly string[]).includes(raw ?? '') ? (raw as T) : undefined
}

function money(raw: string | undefined): number | undefined {
  if (raw === undefined || raw.trim() === '') return undefined
  const n = Number(raw)
  return Number.isFinite(n) && n >= 0 && n <= 1_000_000 ? n : undefined
}

export function parseFilters(query: LocationQuery): ProgramFilters {
  const sort = oneOf(SORT_KEYS, first(query, 'sort')) ?? 'title'
  const minTuition = money(first(query, 'min_tuition'))
  let maxTuition = money(first(query, 'max_tuition'))
  // A hand-edited URL with max < min would be a 422; keep the lower bound only.
  if (minTuition !== undefined && maxTuition !== undefined && maxTuition < minTuition) maxTuition = undefined
  const page = Number(first(query, 'page') ?? 1)
  return {
    state: first(query, 'state') || undefined,
    q: first(query, 'q')?.trim() ?? '',
    cip: CIP_FAMILIES.filter((f) => asList(query.cip).includes(f)),
    stem: oneOf(STEM_FILTERS, first(query, 'stem')),
    control: INSTITUTION_CONTROLS.filter((c) => asList(query.control).includes(c)),
    city: [...new Set(asList(query.city).map((c) => c.trim()).filter((c) => c && c.length <= 120))].slice(0, MAX_CITIES),
    minTuition,
    maxTuition,
    sevp: oneOf(SEVP_FILTERS, first(query, 'sevp')),
    accredited: oneOf(ACCREDITED_FILTERS, first(query, 'accredited')),
    hasGraduates: oneOf(GRADUATES_FILTERS, first(query, 'has_graduates')),
    sort,
    order: oneOf(['asc', 'desc'] as const, first(query, 'order')) ?? DEFAULT_ORDER[sort],
    page: Number.isInteger(page) && page > 0 ? page : 1,
  }
}

/** Parameters for `GET /api/programs`. */
export function toApiQuery(f: ProgramFilters, pageSize: number): ProgramQuery {
  return {
    kind: 'degree',
    state: f.state,
    cip_family: f.cip,
    stem: f.stem,
    q: f.q || undefined,
    control: f.control,
    city: f.city,
    min_tuition: f.minTuition,
    max_tuition: f.maxTuition,
    sevp: f.sevp,
    accredited: f.accredited,
    has_graduates: f.hasGraduates,
    sort: f.sort,
    order: f.order,
    limit: pageSize,
    offset: (f.page - 1) * pageSize,
  }
}

/** URL query for a filter state; defaults are left out so links stay short. */
export function toUrlQuery(f: ProgramFilters, extra: LocationQueryRaw = {}): LocationQueryRaw {
  const query: LocationQueryRaw = {
    ...extra,
    state: f.state,
    q: f.q || undefined,
    cip: f.cip,
    stem: f.stem,
    control: f.control,
    city: f.city,
    min_tuition: f.minTuition === undefined ? undefined : String(f.minTuition),
    max_tuition: f.maxTuition === undefined ? undefined : String(f.maxTuition),
    sevp: f.sevp,
    accredited: f.accredited,
    has_graduates: f.hasGraduates,
    sort: f.sort === 'title' ? undefined : f.sort,
    order: f.order === DEFAULT_ORDER[f.sort] ? undefined : f.order,
    page: f.page > 1 ? String(f.page) : undefined,
  }
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0)) delete query[key]
  }
  return query
}

/** How many filter groups are active (shown as "Filters (n)"); sort and page are not filters. */
export function activeFilterCount(f: ProgramFilters): number {
  return [
    !!f.state,
    !!f.q,
    f.cip.length > 0,
    !!f.stem,
    f.control.length > 0,
    f.city.length > 0,
    f.minTuition !== undefined || f.maxTuition !== undefined,
    !!f.sevp,
    !!f.accredited,
    !!f.hasGraduates,
  ].filter(Boolean).length
}

/** Same sort, no filters (every state), page 1. */
export function clearedFilters(f: ProgramFilters): ProgramFilters {
  return { q: '', cip: [], control: [], city: [], sort: f.sort, order: f.order, page: 1 }
}
