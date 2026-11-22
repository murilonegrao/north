import type { CourseDetail, CourseList, Facets, ProgramDetail, ProgramKind, ProgramList, ProgramQuery } from './types'

export const API_BASE = '/api'

/** An HTTP error from the API, or `status: 0` when the API could not be reached. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' }, signal })
  } catch (error) {
    if ((error as Error)?.name === 'AbortError') throw error
    throw new ApiError(0, 'network error')
  }
  if (!response.ok) throw new ApiError(response.status, `HTTP ${response.status}`)
  try {
    return (await response.json()) as T
  } catch {
    // A proxy error page (API down behind Vite) is HTML, not JSON.
    throw new ApiError(0, 'invalid response')
  }
}

export function programQueryString(query: ProgramQuery): string {
  const params = new URLSearchParams()
  if (query.country) params.set('country', query.country)
  if (query.kind) params.set('kind', query.kind)
  if (query.state) params.set('state', query.state)
  for (const family of query.cip_family ?? []) params.append('cip_family', family)
  if (query.stem) params.set('stem', query.stem)
  if (query.q) params.set('q', query.q)
  for (const control of query.control ?? []) params.append('control', control)
  for (const city of query.city ?? []) params.append('city', city)
  if (query.min_tuition !== undefined) params.set('min_tuition', String(query.min_tuition))
  if (query.max_tuition !== undefined) params.set('max_tuition', String(query.max_tuition))
  if (query.sevp) params.set('sevp', query.sevp)
  if (query.accredited) params.set('accredited', query.accredited)
  if (query.has_graduates) params.set('has_graduates', query.has_graduates)
  for (const exam of query.exam ?? []) params.append('exam', exam)
  if (query.cefr_entry_max) params.set('cefr_entry_max', query.cefr_entry_max)
  if (query.hours_min !== undefined) params.set('hours_min', String(query.hours_min))
  if (query.sort) params.set('sort', query.sort)
  if (query.order) params.set('order', query.order)
  if (query.limit !== undefined) params.set('limit', String(query.limit))
  if (query.offset !== undefined) params.set('offset', String(query.offset))
  const text = params.toString()
  return text ? `?${text}` : ''
}

export function listPrograms(query: ProgramQuery, signal?: AbortSignal): Promise<ProgramList> {
  return getJson<ProgramList>(`/programs${programQueryString(query)}`, signal)
}

export function getProgram(id: string, signal?: AbortSignal): Promise<ProgramDetail> {
  return getJson<ProgramDetail>(`/programs/${encodeURIComponent(id)}`, signal)
}

export function getFacets(state?: string, signal?: AbortSignal, scope: { country?: string; kind?: ProgramKind } = {}): Promise<Facets> {
  const params = new URLSearchParams()
  if (scope.country) params.set('country', scope.country)
  if (scope.kind) params.set('kind', scope.kind)
  if (state) params.set('state', state)
  const qs = params.toString()
  return getJson<Facets>(`/facets${qs ? `?${qs}` : ''}`, signal)
}

/** Irish English courses (v0.4): the program list with `country=IE&kind=language_course`. */
export function listCourses(query: ProgramQuery, signal?: AbortSignal): Promise<CourseList> {
  return getJson<CourseList>(`/programs${programQueryString({ ...query, country: 'IE', kind: 'language_course' })}`, signal)
}

export function getCourse(id: string, signal?: AbortSignal): Promise<CourseDetail> {
  return getJson<CourseDetail>(`/programs/${encodeURIComponent(id)}`, signal)
}
