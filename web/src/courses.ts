// English courses in Ireland (record 0008, slice E2): URL filters, API query and display names.
// The URL is the single source of truth (NFR-15: shareable links), as on the program list.
import type { LocationQuery, LocationQueryRaw } from 'vue-router'
import { CEFR_BANDS, type CefrBand, EXAMS, type Exam, type ProgramQuery } from './api/types'
import type { PlacementResult } from './placement/result'

export const HOURS_OPTIONS = [15, 20, 25] as const

export interface CourseFilters {
  city?: string
  exam?: Exam
  /** Entry level at or below this band. */
  level?: CefrBand
  hoursMin?: number
  /** "Up to my level": the level comes from the last placement result in this browser. */
  mine: boolean
  page: number
}

function one(value: LocationQuery[string] | undefined): string | undefined {
  const v = Array.isArray(value) ? value[0] : value
  return typeof v === 'string' && v.trim() ? v.trim() : undefined
}

export function parseCourseFilters(query: LocationQuery): CourseFilters {
  const exam = one(query.exam)
  const level = one(query.level)
  const hours = Number(one(query.hours))
  const page = Number(one(query.page))
  const city = one(query.city)
  return {
    city: city && city.length <= 120 ? city : undefined,
    exam: (EXAMS as readonly string[]).includes(exam ?? '') ? (exam as Exam) : undefined,
    level: (CEFR_BANDS as readonly string[]).includes(level ?? '') ? (level as CefrBand) : undefined,
    hoursMin: (HOURS_OPTIONS as readonly number[]).includes(hours) ? hours : undefined,
    mine: one(query.mine) === '1',
    page: Number.isInteger(page) && page > 1 ? page : 1,
  }
}

export function toCourseUrlQuery(f: CourseFilters): LocationQueryRaw {
  return {
    city: f.city,
    exam: f.exam,
    level: f.mine ? undefined : f.level,
    hours: f.hoursMin !== undefined ? String(f.hoursMin) : undefined,
    mine: f.mine ? '1' : undefined,
    page: f.page > 1 ? String(f.page) : undefined,
  }
}

/** The course entry band a placement level allows: below A2 means A1 courses and below. */
export function placementBand(result: PlacementResult | null): CefrBand | null {
  if (!result) return null
  return result.overall === 'below_A2' ? 'A1' : result.overall
}

/** The level filter in force: the placement band when "up to my level" is on. */
export function effectiveLevel(f: CourseFilters, mine: CefrBand | null): CefrBand | undefined {
  return f.mine && mine ? mine : f.level
}

export function toCourseApiQuery(f: CourseFilters, pageSize: number, mine: CefrBand | null): ProgramQuery {
  return {
    city: f.city ? [f.city] : undefined,
    exam: f.exam ? [f.exam] : undefined,
    cefr_entry_max: effectiveLevel(f, mine),
    hours_min: f.hoursMin,
    limit: pageSize,
    offset: (f.page - 1) * pageSize,
  }
}

export function activeCourseFilterCount(f: CourseFilters): number {
  return [f.city, f.exam, f.mine ? 'mine' : f.level, f.hoursMin].filter((v) => v !== undefined).length
}

/** Exam names are proper names, not translated; `other` is translated by the view. */
export const EXAM_NAMES: Record<Exam, string> = {
  ielts: 'IELTS',
  cambridge: 'Cambridge English',
  trinity: 'Trinity ISE',
  languagecert: 'LanguageCert',
  toefl: 'TOEFL',
  pte: 'PTE',
  duolingo: 'Duolingo English Test',
  tie: 'TIE (Test of Interactive English)',
  other: 'other',
}

/** Names of the official lists (proper names). */
export const LIST_NAMES: Record<string, string> = {
  ie_ilep: 'ILEP',
  ie_trusted: 'TrustEd Ireland',
}
