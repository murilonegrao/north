// @vitest-environment happy-dom
// Review fixes: safe links, language switch keeps query/hash and the program title, null fields.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { RouterView } from 'vue-router'
import { FIXTURE_DETAILS, FIXTURE_PROGRAMS } from '../mock/fixtures'
import { handleMockRequest } from '../mock/handlers'
import type { ProgramDetail, ProgramList } from '../src/api/types'
import LanguageSwitcher from '../src/components/LanguageSwitcher.vue'
import VerifiedField from '../src/components/VerifiedField.vue'
import { placeLabel, safeHttpUrl } from '../src/format'
import { makeI18n, makeRouter, stubFetchWithMock } from './helpers'

const Root = defineComponent({ render: () => h('div', [h(LanguageSwitcher), h(RouterView)]) })

async function mountAt(path: string) {
  const router = makeRouter()
  // Like the app router: every navigation resets the generic page title.
  router.afterEach(() => {
    document.title = 'Programs · North'
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(Root, { global: { plugins: [makeI18n(), router] } })
  await flushPromises()
  return { wrapper, router }
}

/** Mock API, with some responses replaced. */
function stubFetch(overrides: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      const path = url.split('?')[0]!
      if (path in overrides) return new Response(JSON.stringify(overrides[path]), { status: 200 })
      const result = handleMockRequest(url)
      if (!result) throw new TypeError('unexpected request')
      return new Response(JSON.stringify(result.body), { status: result.status })
    }),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('safeHttpUrl and placeLabel', () => {
  it('accepts only http and https', () => {
    expect(safeHttpUrl('https://example.edu/a')).toBe('https://example.edu/a')
    expect(safeHttpUrl('http://example.edu/')).toBe('http://example.edu/')
    for (const bad of ['javascript:alert(1)', 'JaVaScRiPt:alert(1)', ' javascript:alert(1)', 'data:text/html,x', 'vbscript:x', '/relative', 'not a url', '', null, undefined]) {
      expect(safeHttpUrl(bad)).toBeNull()
    }
  })

  it('never renders ", TX"', () => {
    expect(placeLabel('Austin', 'TX')).toBe('Austin, TX')
    expect(placeLabel(null, 'TX')).toBe('TX')
  })
})

describe('VerifiedField source link', () => {
  const mountField = (sourceUrl: string) =>
    mount(VerifiedField, { props: { label: 'L', status: 'confirmed_official', sourceUrl }, global: { plugins: [makeI18n()] } })

  it('links an https source', () => {
    const w = mountField('https://example.gov/list.csv')
    expect(w.find('a').attributes('href')).toBe('https://example.gov/list.csv')
  })

  it('shows a javascript: URL as text, never as a link', () => {
    const w = mountField('javascript:alert(1)')
    expect(w.find('a').exists()).toBe(false)
    expect(w.find('[data-test="source-text"]').text()).toContain('javascript:alert(1)')
  })
})

describe('null fields in the views', () => {
  it('list: unknown city shows the state alone', async () => {
    const base = handleMockRequest('/api/programs?limit=25')!.body as ProgramList
    const item = { ...base.items[0]!, campus: { city: null, state: 'TX' }, institution: { ...base.items[0]!.institution, control: null } }
    stubFetch({ '/api/programs': { ...base, total: 1, items: [item] } })
    const { wrapper } = await mountAt('/en/programs')
    const where = wrapper.find('.program-where').text()
    expect(where).toBe(`${item.institution.name} · TX`)
    expect(wrapper.text()).not.toContain('null')
    expect(wrapper.text()).not.toContain(', TX')
  })

  it('detail: null control, city, rows and unsafe URLs', async () => {
    const id = FIXTURE_PROGRAMS[0]!.id
    const d: ProgramDetail = structuredClone(FIXTURE_DETAILS[id]!)
    d.institution.control = null
    d.institution.website = 'javascript:alert(document.cookie)'
    d.campus.city = null
    d.stem_opt.source_url = 'javascript:alert(1)'
    d.sources = d.sources.map((s, n) => (n === 0 ? { ...s, rows: null } : s))
    stubFetch({ [`/api/programs/${id}`]: d })
    const { wrapper } = await mountAt(`/en/programs/${id}`)
    const text = wrapper.text()
    expect(text).not.toContain('null')
    expect(text).not.toContain('()')
    expect(text).not.toContain(', TX')
    expect(text).not.toContain('0 rows')
    expect(text).toContain('public or private: unknown')
    expect(text).toContain('row count not recorded')
    for (const a of wrapper.findAll('a')) expect(a.attributes('href') ?? '').not.toMatch(/^\s*javascript:/i)
    expect(wrapper.find('[data-test="website-text"]').text()).toBe('javascript:alert(document.cookie)')
    expect(document.querySelector('meta[name="description"]')?.getAttribute('content') ?? '').not.toContain('()')
  })
})

describe('language switch', () => {
  it('keeps the filters (query) and the hash on the list', async () => {
    stubFetchWithMock()
    const { wrapper, router } = await mountAt('/en/programs?cip=52.12&stem=not_eligible&sort=tuition#results')
    await wrapper.find('.switcher select').setValue('pt-br')
    await flushPromises()
    const route = router.currentRoute.value
    expect(route.path).toBe('/pt-br/programs')
    expect(route.query).toEqual({ cip: '52.12', stem: 'not_eligible', sort: 'tuition' })
    expect(route.hash).toBe('#results')
  })

  it('keeps the program title as the tab title on a detail page', async () => {
    stubFetchWithMock()
    const p = FIXTURE_PROGRAMS[0]!
    const { wrapper, router } = await mountAt(`/en/programs/${p.id}`)
    expect(document.title).toContain(p.title)
    await wrapper.find('.switcher select').setValue('pt-br')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe(`/pt-br/programs/${p.id}`)
    expect(document.title).toContain(p.title)
    expect(document.title).not.toBe('Programs · North')
  })
})

describe('build and CSP', () => {
  it('never inlines fonts as data: URIs (CSP font-src is self only)', async () => {
    const { default: config } = await import('../vite.config')
    const resolved = typeof config === 'function' ? await config({ mode: 'production', command: 'build' }) : config
    const limit = resolved.build?.assetsInlineLimit
    expect(typeof limit).toBe('function')
    const decide = limit as (file: string, content: Buffer) => boolean | undefined
    expect(decide('inter-latin-wght-normal.woff2', Buffer.alloc(10))).toBe(false)
    expect(decide('icon.svg', Buffer.alloc(10))).toBeUndefined()
  })
})

describe('dark theme form fields', () => {
  it('inputs and selects use the 3:1 field border token, not the panel border', async () => {
    const { readFileSync } = await import('node:fs')
    const read = (p: string) => readFileSync(new URL(p, import.meta.url), 'utf8')
    expect(read('../src/styles/tokens.css')).toMatch(/--field-border:\s*var\(--text-muted\)/)
    for (const file of ['../src/components/ProgramFilters.vue', '../src/components/LanguageSwitcher.vue', '../src/views/ProgramListView.vue']) {
      expect(read(file)).toContain('border: 1px solid var(--field-border)')
    }
  })
})
