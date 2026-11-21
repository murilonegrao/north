import type { Facets, ProgramDetail, ProgramList, ProgramQuery } from './types'

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

export function getFacets(state?: string, signal?: AbortSignal): Promise<Facets> {
  const qs = state ? `?${new URLSearchParams({ state })}` : ''
  return getJson<Facets>(`/facets${qs}`, signal)
}
