import { vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import { handleMockRequest } from '../mock/handlers'
import en from '../src/locales/en.json'
import ProgramDetailView from '../src/views/ProgramDetailView.vue'
import ProgramListView from '../src/views/ProgramListView.vue'

export function makeI18n() {
  const { _meta: _ignored, ...messages } = en as Record<string, unknown>
  return createI18n({ legacy: false, locale: 'en', messages: { en: messages as never }, missingWarn: false, fallbackWarn: false })
}

export function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/:lang/', component: { template: '<div />' } },
      { path: '/:lang/programs', component: ProgramListView },
      { path: '/:lang/programs/:id', component: ProgramDetailView },
    ],
  })
}

/** Route fetch('/api/...') to the fictitious mock API. */
export function stubFetchWithMock() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const result = handleMockRequest(String(input))
    if (!result) throw new TypeError('unexpected request')
    return new Response(JSON.stringify(result.body), { status: result.status, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

export function stubFetchDown() {
  vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
}
