// @vitest-environment happy-dom
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { RouterView } from 'vue-router'
import { FIXTURE_PROGRAMS } from '../mock/fixtures'
import { handleMockRequest } from '../mock/handlers'
import type { Facets } from '../src/api/types'
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

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('program list', () => {
  it('renders fixture rows with the result count', async () => {
    stubFetchWithMock()
    const { wrapper } = await mountAt('/en/programs')
    const rows = wrapper.findAll('[data-test="program-row"]')
    expect(rows.length).toBe(Math.min(25, FIXTURE_PROGRAMS.length))
    expect(wrapper.text()).toContain(`${FIXTURE_PROGRAMS.length} programs`)
    expect(wrapper.text()).toContain('Example State University')
    expect(wrapper.find('nav.pagination').exists()).toBe(true)
  })

  it('sends URL filters to the API and explains the 52.12 flag', async () => {
    const fetchMock = stubFetchWithMock()
    const { wrapper } = await mountAt('/en/programs?cip=52.12&stem=not_eligible')
    const url = String(fetchMock.mock.calls[0]?.[0])
    expect(url).toContain('cip_family=52.12')
    expect(url).toContain('stem=not_eligible')
    const rows = wrapper.findAll('[data-test="program-row"]')
    expect(rows.length).toBeGreaterThan(0)
    for (const row of rows) expect(row.text()).toContain('No STEM OPT extension.')
  })

  it('stem=unknown follows v0.1 semantics (status unknown only)', async () => {
    stubFetchWithMock()
    const { wrapper } = await mountAt('/en/programs?stem=unknown')
    const expected = FIXTURE_PROGRAMS.filter((p) => p.stem_opt.status === 'unknown').length
    expect(expected).toBeGreaterThan(0)
    const rows = wrapper.findAll('[data-test="program-row"]')
    expect(rows).toHaveLength(expected)
    for (const row of rows) expect(row.text()).toContain('Eligibility unknown')
  })

  it('shows a friendly message when the API is down', async () => {
    stubFetchDown()
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    const { wrapper } = await mountAt('/en/programs')
    expect(wrapper.find('[role="alert"]').text()).toContain('could not be loaded')
    expect(wrapper.find('[role="alert"] button').text()).toBe('Try again')
  })
})

describe('program list v0.2', () => {
  const programCalls = (fetchMock: ReturnType<typeof stubFetchWithMock>) =>
    fetchMock.mock.calls.map((c) => String(c[0])).filter((u) => u.startsWith('/api/programs'))

  it('shows the price with its badge and qualifier, and Unknown (never $0) when unknown', async () => {
    stubFetchWithMock()
    const { wrapper } = await mountAt('/en/programs?sort=tuition&order=desc')
    const rows = wrapper.findAll('[data-test="program-row"]')
    const first = rows[0]!
    const top = Math.max(...FIXTURE_PROGRAMS.map((p) => p.graduate_tuition_nonresident.value?.amount ?? 0))
    const price = first.find('[data-test="tuition"]')
    expect(first.text()).toContain('Graduate tuition (nonresident)')
    expect(price.text()).toContain(`$${top.toLocaleString('en')} / year`)
    expect(price.find('.badge--confirmed_official').exists()).toBe(true)
    expect(price.find('.qualifier').text()).toBe('institution average')
    const tipId = price.find('.qualifier').attributes('aria-describedby')!
    expect(price.find(`[id="${tipId}"]`).text()).toBe("Institution-wide average for graduate students, not this program's price.")

    // Unknown tuition sorts last, so the last row of the last page has it.
    const unknownRows = FIXTURE_PROGRAMS.filter((p) => p.graduate_tuition_nonresident.status === 'unknown').length
    expect(unknownRows).toBeGreaterThan(0)
    const { wrapper: last } = await mountAt('/en/programs?sort=tuition&order=asc&page=2')
    const unknown = last.findAll('[data-test="program-row"]').at(-1)!.find('[data-test="tuition"]')
    expect(unknown.attributes('data-status')).toBe('unknown')
    expect(unknown.text()).toContain('Unknown')
    expect(unknown.text()).not.toContain('$')
    expect(unknown.find('.badge--unknown').exists()).toBe(true)
  })

  it('shows a missing nonresident count as Unknown with its badge, never 0', async () => {
    stubFetchWithMock()
    const target = FIXTURE_PROGRAMS.find((p) => p.completions.value && p.completions.value.nonresident === null)!
    expect(target).toBeDefined()
    const { wrapper } = await mountAt(`/en/programs?q=${encodeURIComponent(target.institution.name)}&limit=200`)
    const row = wrapper.findAll('[data-test="program-row"]').find((r) => r.find(`a[href$="${target.id}"]`).exists())!
    const line = row.find('[data-test="completions"]')
    expect(line.text()).toContain(`${target.completions.value!.total} total (2023-24)`)
    expect(line.text()).not.toMatch(/\b0 nonresident/)
    expect(line.find('[data-test="nonresident-unknown"] .badge--unknown').exists()).toBe(true)
  })

  it('maps filter clicks to the URL query and the API request, and clears them all', async () => {
    const fetchMock = stubFetchWithMock()
    const { wrapper, router } = await mountAt('/en/programs')
    const control = wrapper.find('[data-test="filter-control"]')
    await control.findAll('input[type="checkbox"]')[2]!.setValue(true) // private for-profit
    await flushPromises()
    expect(router.currentRoute.value.query.control).toEqual(['private_for_profit'])
    expect(programCalls(fetchMock).at(-1)).toContain('control=private_for_profit')

    await wrapper.find('input[name="sevp"][value="unknown"]').setValue(true)
    await flushPromises()
    expect(router.currentRoute.value.query.sevp).toBe('unknown')
    expect(programCalls(fetchMock).at(-1)).toContain('sevp=unknown')

    const min = wrapper.find('[data-test="tuition-min"]')
    await min.setValue('10000')
    await min.trigger('change')
    await flushPromises()
    expect(router.currentRoute.value.query.min_tuition).toBe('10000')
    expect(programCalls(fetchMock).at(-1)).toContain('min_tuition=10000')
    expect(wrapper.find('[data-test="filters-toggle"]').text()).toContain('Filters (3)')

    await wrapper.find('[data-test="clear-filters"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('rejects max below min in the form without touching the URL', async () => {
    stubFetchWithMock()
    const { wrapper, router } = await mountAt('/en/programs?min_tuition=20000')
    const max = wrapper.find('[data-test="tuition-max"]')
    await max.setValue('100')
    await max.trigger('change')
    await flushPromises()
    expect(wrapper.find('#tuition-error').text()).toContain('at least the minimum')
    expect(router.currentRoute.value.query.max_tuition).toBeUndefined()
  })

  it("sort select uses each field's default order, and the toggle flips it", async () => {
    const fetchMock = stubFetchWithMock()
    const { wrapper, router } = await mountAt('/en/programs')
    expect(programCalls(fetchMock)[0]).toContain('sort=title&order=asc')
    await wrapper.find('[data-test="sort-select"]').setValue('graduates')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ sort: 'graduates' })
    expect(programCalls(fetchMock).at(-1)).toContain('sort=graduates&order=desc')
    const toggle = wrapper.find('[data-test="order-toggle"]')
    expect(toggle.attributes('aria-label')).toBe('Sort order: Descending. Activate to switch to Ascending.')
    await toggle.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ sort: 'graduates', order: 'asc' })
    expect(programCalls(fetchMock).at(-1)).toContain('sort=graduates&order=asc')
    await wrapper.find('[data-test="sort-select"]').setValue('tuition')
    await flushPromises()
    expect(programCalls(fetchMock).at(-1)).toContain('sort=tuition&order=asc')
  })

  it('shows facet counts next to the options', async () => {
    const fetchMock = stubFetchWithMock()
    const { wrapper } = await mountAt('/en/programs')
    expect(fetchMock.mock.calls.some((c) => String(c[0]).startsWith('/api/facets'))).toBe(true)
    const facets = handleMockRequest('/api/facets')!.body as Facets
    const control = wrapper.find('[data-test="filter-control"]')
    const counts = control.findAll('[data-test="facet-count"]').map((n) => n.text())
    expect(counts).toEqual([facets.control.public, facets.control.private_nonprofit, facets.control.private_for_profit].map(String))
    const firstCity = wrapper.find('.city-list .option')
    expect(firstCity.text()).toContain(facets.cities[0]!.city)
    expect(firstCity.find('[data-test="facet-count"]').text()).toBe(String(facets.cities[0]!.count))
    expect(wrapper.find('[data-test="tuition-min"]').attributes('placeholder')).toBe(`$${facets.tuition.min!.toLocaleString('en')}`)
  })

  it('table view has sortable headers with aria-sort', async () => {
    stubFetchWithMock()
    const { wrapper, router } = await mountAt('/en/programs?view=table&sort=tuition')
    const table = wrapper.find('[data-test="program-table"]')
    expect(table.exists()).toBe(true)
    expect(table.find('th[aria-sort]').attributes('aria-sort')).toBe('ascending')
    expect(table.find('th[aria-sort] button').attributes('data-sort')).toBe('tuition')
    await table.find('button[data-sort="tuition"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ view: 'table', sort: 'tuition', order: 'desc' })
    await wrapper.find('button[data-sort="institution"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ sort: 'institution' })
    expect(wrapper.find('th[aria-sort] button').attributes('data-sort')).toBe('institution')
  })
})

describe('program detail', () => {
  it('shows values with badges, the tuition note and the "Not yet collected" section', async () => {
    stubFetchWithMock()
    const id = FIXTURE_PROGRAMS[0]!.id
    const { wrapper } = await mountAt(`/en/programs/${id}`)
    const missing = wrapper.find('[data-test="not-collected"]')
    expect(missing.exists()).toBe(true)
    expect(missing.text()).toContain('Not yet collected')
    expect(missing.text()).toContain('Minimum English test score')
    expect(missing.text()).toContain('Whether the school issues an I-20')
    expect(missing.findAll('li')).toHaveLength(6)
    expect(wrapper.find('[data-test="tuition-note"]').text()).toBe(
      "Institution-wide average for graduate students, not this program's price.",
    )
    // v0.1: STEM OPT and completions are VerifiedValues with badges and dates.
    const fields = wrapper.findAll('.field')
    const stem = fields.find((f) => f.find('dt').text() === 'STEM OPT')!
    expect(stem.find('.badge').exists()).toBe(true)
    expect(stem.text()).toContain('Checked')
    const graduates = fields.find((f) => f.find('dt').text() === 'Graduates')!
    expect(graduates.find('.badge--confirmed_official').exists()).toBe(true)
    expect(graduates.text()).toContain('Checked')
    // Fixed source ids map to readable names.
    expect(wrapper.text()).toContain('DHS STEM designated degree program list')
    expect(wrapper.text()).not.toContain('dhs_stem_list')
    const sourceLinks = wrapper.findAll('a[target="_blank"]')
    expect(sourceLinks.length).toBeGreaterThan(0)
    for (const link of sourceLinks) expect(link.attributes('rel')).toContain('noopener')
  })

  it('says so when the program does not exist', async () => {
    stubFetchWithMock()
    const { wrapper } = await mountAt('/en/programs/000000-000000')
    expect(wrapper.text()).toContain('Program not found')
  })
})
