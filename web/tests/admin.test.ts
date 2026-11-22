// @vitest-environment happy-dom
// Admin area: message parity, the route guard, and the two-step sign-in.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type RouteLocationNormalized } from 'vue-router'
import { adminGuard } from '../src/admin/guard'
import { tokenFromHash } from '../src/admin/links'
import en from '../src/admin/locales/en.json'
import ptBR from '../src/admin/locales/pt-BR.json'
import { session } from '../src/admin/session'
import type { SessionState } from '../src/admin/types'
import LoginView from '../src/admin/views/LoginView.vue'
import { i18n } from '../src/i18n'

type Tree = { [key: string]: string | Tree }
function leaves(tree: Tree, prefix = ''): string[] {
  return Object.entries(tree).flatMap(([k, v]) =>
    typeof v === 'string' ? [prefix + k] : leaves(v, `${prefix}${k}.`),
  )
}
function load(messages: Record<string, unknown>): Tree {
  const { _meta: _ignored, ...rest } = messages
  return rest as Tree
}

const user = { id: 1, username: 'ana', role: 'viewer', has_totp: true, disabled: false, must_change_password: false, last_login_at: null, created_at: '2026-11-22T00:00:00Z', email: null, email_verified: false, locale: 'en', notify_jobs: true }
const state = (stage: string, role = 'viewer', csrf = 'csrf-1'): SessionState =>
  ({ user: { ...user, role }, stage, csrf }) as SessionState

function stubApi(routes: Record<string, (init: RequestInit) => [number, unknown]>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const path = String(input).replace('/api/admin', '')
    const handler = routes[`${init.method ?? 'GET'} ${path}`]
    if (!handler) return new Response('{}', { status: 404 })
    const [status, body] = handler(init)
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const route = (name: string, minRole?: string, isPublic = false) =>
  ({ name, meta: { admin: true, minRole, public: isPublic }, path: '/admin' }) as unknown as RouteLocationNormalized

beforeEach(() => {
  session.loaded = false
  session.user = null
  session.stage = null
  session.csrf = ''
})
afterEach(() => vi.unstubAllGlobals())

describe('admin messages', () => {
  it('pt-BR has exactly the keys of en', () => {
    expect(leaves(load(ptBR)).sort()).toEqual(leaves(load(en)).sort())
  })
})

describe('admin guard', () => {
  it('sends a visitor without a session to the sign-in page', async () => {
    stubApi({ 'GET /auth/me': () => [401, { detail: 'login required' }] })
    expect(await adminGuard(route('admin-overview'))).toBe('/admin/login')
    expect(await adminGuard(route('admin-login'))).toBe(true)
  })

  it('keeps a first sign-in on the setup page until it is secured', async () => {
    stubApi({ 'GET /auth/me': () => [200, state('enroll_totp')] })
    expect(await adminGuard(route('admin-jobs'))).toBe('/admin/setup')
    expect(await adminGuard(route('admin-setup'))).toBe(true)
  })

  it('enforces the role of the page', async () => {
    stubApi({ 'GET /auth/me': () => [200, state('ok', 'viewer')] })
    expect(await adminGuard(route('admin-users', 'admin'))).toBe('/admin')
    expect(await adminGuard(route('admin-jobs'))).toBe(true)
    expect(await adminGuard(route('admin-login'))).toBe('/admin')
  })
})

describe('sign-in', () => {
  it('asks for the code after the password and sends the CSRF token with it', async () => {
    const fetchMock = stubApi({
      'POST /auth/login': () => [200, state('totp', 'admin', 'pending-csrf')],
      'POST /auth/totp': (init) => {
        const headers = init.headers as Record<string, string>
        return headers['X-CSRF-Token'] === 'pending-csrf' ? [200, state('ok', 'admin', 'full-csrf')] : [403, {}]
      },
    })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/admin/login', component: LoginView },
        { path: '/admin', component: { template: '<p>home</p>' } },
      ],
    })
    await router.push('/admin/login')
    const wrapper = mount(LoginView, { global: { plugins: [i18n, router] } })
    await wrapper.find('#login-user').setValue('ana')
    await wrapper.find('#login-password').setValue('a long pass phrase')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('#login-code').exists()).toBe(true)
    await wrapper.find('#login-code').setValue('123456')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(session.stage).toBe('ok')
    expect(session.csrf).toBe('full-csrf')
    expect(router.currentRoute.value.path).toBe('/admin')
  })

  it('shows the throttling message on 429', async () => {
    stubApi({ 'POST /auth/login': () => [429, { detail: 'too many attempts' }] })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: LoginView }] })
    const wrapper = mount(LoginView, { global: { plugins: [i18n, router] } })
    const { loadAdminMessages } = await import('../src/admin/i18n')
    await loadAdminMessages()
    await wrapper.find('#login-user').setValue('ana')
    await wrapper.find('#login-password').setValue('x')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Too many attempts')
  })
})

describe('email links', () => {
  it('reads the token from the fragment only when it looks like one', () => {
    expect(tokenFromHash('#token=abcDEF_123-xyz')).toBe('abcDEF_123-xyz')
    expect(tokenFromHash('#token=short')).toBe('')
    expect(tokenFromHash('#token=<script>alert(1)</script>')).toBe('')
    expect(tokenFromHash('')).toBe('')
  })

  it('opens the reset and verification pages without a session', async () => {
    stubApi({ 'GET /auth/me': () => [401, { detail: 'login required' }] })
    expect(await adminGuard(route('admin-reset', undefined, true))).toBe(true)
    expect(await adminGuard(route('admin-verify-email', undefined, true))).toBe(true)
    expect(await adminGuard(route('admin-overview'))).toBe('/admin/login')
  })
})
