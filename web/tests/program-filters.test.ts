// URL <-> filter state <-> API query mapping (contract v0.2 §2), and the mock implementing it.
import { describe, expect, it } from 'vitest'
import { programQueryString } from '../src/api/client'
import type { Facets, ProgramList } from '../src/api/types'
import { formatMoney } from '../src/format'
import { activeFilterCount, clearedFilters, parseFilters, toApiQuery, toUrlQuery } from '../src/programFilters'
import { handleMockRequest } from '../mock/handlers'

function list(qs: string): ProgramList {
  const r = handleMockRequest(`/api/programs?${qs}`)!
  expect(r.status).toBe(200)
  return r.body as ProgramList
}

describe('filter state mapping', () => {
  it('reads every v0.2 filter from the URL and sends it to the API', () => {
    const f = parseFilters({
      q: ' data ',
      cip: ['11', 'bogus'],
      control: ['public', 'private_for_profit', 'state'],
      city: ['Austin', 'Houston', 'Austin'],
      min_tuition: '5000',
      max_tuition: '30000',
      sevp: 'confirmed',
      accredited: 'unknown',
      has_graduates: 'true',
      sort: 'tuition',
      page: '2',
    })
    expect(f).toMatchObject({ q: 'data', cip: ['11'], control: ['public', 'private_for_profit'], city: ['Austin', 'Houston'] })
    expect(f.order).toBe('asc') // tuition defaults to cheapest first
    const qs = programQueryString(toApiQuery(f, 25))
    const params = new URLSearchParams(qs.slice(1))
    expect(params.getAll('control')).toEqual(['public', 'private_for_profit'])
    expect(params.getAll('city')).toEqual(['Austin', 'Houston'])
    expect(params.get('min_tuition')).toBe('5000')
    expect(params.get('max_tuition')).toBe('30000')
    expect(params.get('sevp')).toBe('confirmed')
    expect(params.get('accredited')).toBe('unknown')
    expect(params.get('has_graduates')).toBe('true')
    expect(params.get('sort')).toBe('tuition')
    expect(params.get('order')).toBe('asc')
    expect(params.get('offset')).toBe('25')
    expect(activeFilterCount(f)).toBe(8)
  })

  it('ignores invalid values instead of sending a request the API would reject', () => {
    const f = parseFilters({ sevp: 'yes', accredited: 'false', has_graduates: 'maybe', sort: 'price', order: 'up', min_tuition: '-5', max_tuition: 'abc' })
    expect(f).toMatchObject({ sevp: undefined, accredited: undefined, hasGraduates: undefined, sort: 'title', order: 'asc' })
    expect(f.minTuition).toBeUndefined()
    expect(f.maxTuition).toBeUndefined()
    // max < min: keep only the lower bound.
    const g = parseFilters({ min_tuition: '20000', max_tuition: '10000' })
    expect([g.minTuition, g.maxTuition]).toEqual([20000, undefined])
  })

  it('uses each field\'s natural order and keeps defaults out of the URL', () => {
    expect(parseFilters({ sort: 'graduates' }).order).toBe('desc')
    expect(parseFilters({ sort: 'nonresident_share' }).order).toBe('desc')
    expect(parseFilters({ sort: 'city' }).order).toBe('asc')
    expect(toUrlQuery(parseFilters({}))).toEqual({})
    expect(toUrlQuery(parseFilters({ sort: 'graduates' }))).toEqual({ sort: 'graduates' })
    expect(toUrlQuery(parseFilters({ sort: 'graduates', order: 'asc' }))).toEqual({ sort: 'graduates', order: 'asc' })
    expect(toUrlQuery(parseFilters({ min_tuition: '0' }))).toEqual({ min_tuition: '0' })
  })

  it('clearing keeps the sort and drops every filter, the state included (all states)', () => {
    const f = parseFilters({ state: 'TX', control: 'public', city: 'Austin', sevp: 'unknown', sort: 'tuition', order: 'desc', page: '3' })
    expect(toUrlQuery(clearedFilters(f))).toEqual({ sort: 'tuition', order: 'desc' })
    expect(activeFilterCount(f)).toBe(4)
  })

  it('formats money in the viewer\'s locale', () => {
    expect(formatMoney({ amount: 22954, currency: 'USD' }, 'en')).toBe('$22,954')
    expect(formatMoney({ amount: 22954, currency: 'USD' }, 'pt-BR')).toMatch(/US\$\s?22\.954/)
  })
})

describe('mock API v0.2', () => {
  it('sorts with unknowns last in both orders and stable ties', () => {
    for (const order of ['asc', 'desc']) {
      const items = list(`sort=tuition&order=${order}&limit=200`).items
      const amounts = items.map((i) => i.graduate_tuition_nonresident.value?.amount ?? null)
      const known = amounts.filter((a): a is number => a !== null)
      expect(amounts.slice(known.length).every((a) => a === null)).toBe(true)
      expect(known).toEqual([...known].sort((a, b) => (order === 'asc' ? a - b : b - a)))
      expect(amounts.slice(known.length).length).toBeGreaterThan(0)
    }
    const graduates = list('sort=graduates&order=desc&limit=200').items
    expect(graduates.at(-1)!.completions.status).toBe('unknown')
    // A null nonresident count is unknown: last in both orders, for the count and the share.
    for (const key of ['nonresident_graduates', 'nonresident_share']) {
      for (const order of ['asc', 'desc']) {
        const items = list(`sort=${key}&order=${order}&limit=200`).items
        const firstNull = items.findIndex((i) => i.completions.value?.nonresident == null)
        expect(firstNull).toBeGreaterThan(0)
        expect(items.slice(firstNull).filter((i) => i.completions.value?.nonresident != null && i.completions.value.total > 0)).toEqual([])
      }
    }
  })

  it('facets count the same programs the filters return', () => {
    const facets = handleMockRequest('/api/facets')!.body as Facets
    expect(facets.total).toBe(list('limit=200').total)
    for (const [value, n] of Object.entries(facets.control)) expect(list(`control=${value}`).total).toBe(n)
    for (const [value, n] of Object.entries(facets.sevp)) expect(list(`sevp=${value}`).total).toBe(n)
    for (const [value, n] of Object.entries(facets.accredited)) expect(list(`accredited=${value}`).total).toBe(n)
    for (const [value, n] of Object.entries(facets.has_graduates)) expect(list(`has_graduates=${value}`).total).toBe(n)
    for (const c of facets.cities) expect(list(`city=${encodeURIComponent(c.city)}`).total).toBe(c.count)
    expect(list('min_tuition=0').total).toBe(facets.tuition.known)
    expect(facets.tuition.unknown).toBeGreaterThan(0)
  })

  it('rejects what the backend rejects', () => {
    for (const qs of ['sort=price', 'order=up', 'control=state', 'min_tuition=-1', 'min_tuition=5000&max_tuition=4000', 'sevp=yes']) {
      expect(handleMockRequest(`/api/programs?${qs}`)!.status).toBe(422)
    }
  })
})
