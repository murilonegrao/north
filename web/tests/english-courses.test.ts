// @vitest-environment happy-dom
// English courses in Ireland (record 0008, slice E2): list, filters, "up to my level", detail.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { RouterView } from 'vue-router'
import { FIXTURE_COURSES } from '../mock/fixtures'
import { handleMockRequest } from '../mock/handlers'
import { programQueryString } from '../src/api/client'
import type { CourseList, Facets } from '../src/api/types'
import { parseCourseFilters, placementBand, toCourseApiQuery, toCourseUrlQuery } from '../src/courses'
import { saveResult } from '../src/placement/result'
import { makeI18n, makeRouter, stubFetchDown, stubFetchWithMock } from './helpers'

const Root = defineComponent({ render: () => h(RouterView) })

async function mountAt(path: string) {
  const router = makeRouter()
  await router.push(path)
  await router.isReady()
  const wrapper = mount(Root, { global: { plugins: [makeI18n(), router] } })
  await flushPromises()
  return { wrapper, router }
}

const courseCalls = (fetchMock: ReturnType<typeof stubFetchWithMock>) =>
  fetchMock.mock.calls.map((c) => String(c[0])).filter((u) => u.startsWith('/api/programs'))

beforeEach(() => window.localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('course filters', () => {
  it('round-trips through the URL and ignores bad values', () => {
    const f = parseCourseFilters({ city: 'Dublin', exam: 'ielts', level: 'B1', hours: '20', page: '2' })
    expect(f).toEqual({ city: 'Dublin', exam: 'ielts', level: 'B1', hoursMin: 20, mine: false, page: 2 })
    expect(parseCourseFilters(toCourseUrlQuery(f) as never)).toEqual(f)
    expect(parseCourseFilters({ exam: 'toeic', level: 'B3', hours: '7', page: '-1' })).toEqual({ mine: false, page: 1 })
  })

  it('"up to my level" takes the band of the last placement result', () => {
    const f = parseCourseFilters({ mine: '1', level: 'C1' })
    expect(toCourseApiQuery(f, 25, 'B1').cefr_entry_max).toBe('B1')
    expect(toCourseApiQuery(f, 25, null).cefr_entry_max).toBe('C1')
    expect(placementBand({ taken_at: '', bank_version: '0.1', bands: {}, overall: 'below_A2' })).toBe('A1')
    expect(placementBand(null)).toBeNull()
  })

  it('mock filters match the mock facets', () => {
    const facets = handleMockRequest('/api/facets?country=IE&kind=language_course')!.body as Facets
    expect(facets.total).toBe(FIXTURE_COURSES.length)
    for (const [exam, n] of Object.entries(facets.exam)) {
      if (exam === 'unknown') continue
      const list = handleMockRequest(`/api/programs?country=IE&kind=language_course&exam=${exam}`)!.body as CourseList
      expect(list.total).toBe(n)
    }
    const qs = programQueryString({ country: 'IE', kind: 'language_course', exam: ['tie'], cefr_entry_max: 'A2', hours_min: 15 })
    const list = handleMockRequest(`/api/programs${qs}`)!.body as CourseList
    expect(list.items.map((c) => c.title)).toEqual(['English for Everyday Life'])
  })
})

describe('English course list', () => {
  it('shows each course with its facts, unknown price and start dates, and the ILEP notice', async () => {
    const fetchMock = stubFetchWithMock()
    const { wrapper } = await mountAt('/en/english-courses')
    const url = courseCalls(fetchMock)[0]!
    expect(url).toContain('country=IE')
    expect(url).toContain('kind=language_course')
    const rows = wrapper.findAll('[data-test="course-row"]')
    expect(rows).toHaveLength(FIXTURE_COURSES.length)
    expect(wrapper.text()).toContain(`${FIXTURE_COURSES.length} courses`)

    const general = rows.find((r) => r.text().includes('General English'))!
    expect(general.text()).toContain('Example English Academy · Dublin')
    expect(general.text()).toContain('Cambridge English')
    expect(general.get('[data-test="cefr"]').text()).toBe('A1 → B2')
    expect(general.text()).toContain('25 weeks')
    expect(general.text()).toContain('15 h')
    // Price and start dates are unknown, styled as unknown, never as a no or a zero.
    for (const sel of ['[data-test="price"]', '[data-test="start-dates"]']) {
      const cell = general.get(sel)
      expect(cell.text()).toContain('Unknown')
      expect(cell.find('.badge--unknown').exists()).toBe(true)
      expect(cell.find('.badge--confirmed_negative').exists()).toBe(false)
      expect(cell.text()).not.toMatch(/€\s?0|0\s?€/)
    }
    expect(general.get('[data-test="authorization"]').text()).toContain('ILEP')
    expect(general.get('[data-test="ilep-notice"]').text()).toContain('ILEP ends after the second TrustEd round (end of 2026)')

    const trusted = rows.find((r) => r.text().includes('Academic English'))!
    expect(trusted.get('[data-test="authorization"]').text()).toContain('TrustEd Ireland')
    expect(trusted.find('[data-test="ilep-notice"]').exists()).toBe(false)

    const twoTowns = rows.find((r) => r.text().includes('English Plus'))!
    expect(twoTowns.find('[data-test="city-unknown"]').text()).toBe('City unknown')
    const noLevel = rows.find((r) => r.text().includes('Exam Preparation English'))!
    expect(noLevel.text()).toContain('Unknown')
    expect(general.get('a').attributes('href')).toBe('/en/english-courses/ie-ilep-9901-0001')
  })

  it('sends the city, exam, level and hours filters from the URL', async () => {
    const fetchMock = stubFetchWithMock()
    const { wrapper } = await mountAt('/en/english-courses?city=Dublin&exam=ielts&level=B1&hours=20')
    const params = new URLSearchParams(courseCalls(fetchMock)[0]!.split('?')[1])
    expect(params.getAll('city')).toEqual(['Dublin'])
    expect(params.getAll('exam')).toEqual(['ielts'])
    expect(params.get('cefr_entry_max')).toBe('B1')
    expect(params.get('hours_min')).toBe('20')
    const rows = wrapper.findAll('[data-test="course-row"]')
    expect(rows.map((r) => r.get('h2').text())).toEqual(['Intensive English and IELTS'])
  })

  it('changing a select updates the URL', async () => {
    stubFetchWithMock()
    const { wrapper, router } = await mountAt('/en/english-courses')
    await wrapper.get('[data-test="exam-select"]').setValue('tie')
    await flushPromises()
    expect(router.currentRoute.value.query.exam).toBe('tie')
    expect(wrapper.findAll('[data-test="course-row"]')).toHaveLength(1)
  })

  it('"up to my level" is off without a placement result and uses it when there is one', async () => {
    stubFetchWithMock()
    const first = await mountAt('/en/english-courses')
    const toggle = first.wrapper.get('[data-test="mine-toggle"]')
    expect((toggle.element as HTMLInputElement).disabled).toBe(true)
    expect(first.wrapper.get('[data-test="mine"]').text()).toContain('Take the placement test')
    first.wrapper.unmount()

    saveResult({ taken_at: '2026-11-22T12:00:00Z', bank_version: '0.1', bands: { grammar: 'A2' }, overall: 'A2' })
    const fetchMock = stubFetchWithMock()
    const { wrapper, router } = await mountAt('/en/english-courses')
    const mine = wrapper.get('[data-test="mine-toggle"]')
    expect((mine.element as HTMLInputElement).disabled).toBe(false)
    await mine.setValue(true)
    await flushPromises()
    expect(router.currentRoute.value.query.mine).toBe('1')
    const last = courseCalls(fetchMock).at(-1)!
    expect(new URLSearchParams(last.split('?')[1]).get('cefr_entry_max')).toBe('A2')
    const titles = wrapper.findAll('[data-test="course-row"]').map((r) => r.get('h2').text())
    // 'Exam Preparation English' has an unknown entry level: it stays in, marked unknown (BR-02).
    expect(new Set(titles)).toEqual(new Set(['English for Everyday Life', 'English Plus', 'General English', 'Exam Preparation English']))
    expect((wrapper.get('[data-test="level-select"]').element as HTMLSelectElement).disabled).toBe(true)
  })

  it('shows a friendly message when the API is down', async () => {
    stubFetchDown()
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    const { wrapper } = await mountAt('/en/english-courses')
    expect(wrapper.get('[role="alert"]').text()).toContain('could not be loaded')
  })
})

describe('English course detail', () => {
  it('shows every list value with its source, the ILEP rule note, and what is not collected', async () => {
    stubFetchWithMock()
    const { wrapper } = await mountAt('/en/english-courses/ie-ilep-9901-0001')
    expect(wrapper.get('h1').text()).toBe('General English')
    const fields = wrapper.findAll('.field')
    expect(fields.length).toBe(6)
    for (const f of fields) expect(f.find('a[href^="https://"]').exists()).toBe(true)
    expect(wrapper.get('[data-test="rule-note"]').text()).toContain('ILEP ends after the second TrustEd round')
    const missing = wrapper.get('[data-test="not-collected"]').text()
    expect(missing).toContain('Price of the course')
    expect(missing).toContain('Start dates')
    expect(wrapper.text()).toContain('Provider no. 9901')
    expect(wrapper.text()).toContain('ILEP, Interim List of Eligible Programmes')
  })

  it('shows unknown values as unknown with the raw text kept as evidence', async () => {
    stubFetchWithMock()
    const { wrapper } = await mountAt('/en/english-courses/ie-ilep-9903-0001')
    const entry = wrapper.findAll('.field').find((f) => f.text().includes('Entry level'))!
    expect(entry.attributes('data-status')).toBe('unknown')
    expect(entry.text()).toContain('Unknown')
    expect(entry.text()).toContain('Entry Level (fictitious row)')
  })

  it('a degree program id is not a course page', async () => {
    stubFetchWithMock()
    const { wrapper } = await mountAt('/en/english-courses/990001-110701')
    expect(wrapper.get('[role="alert"]').text()).toContain('Course not found')
  })
})
