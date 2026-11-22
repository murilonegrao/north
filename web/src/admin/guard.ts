// Route guard for /admin: messages, language, session stage and role.
import type { RouteLocationNormalized, RouteLocationRaw, Router } from 'vue-router'
import { i18n, preferredLocale, setLocale } from '../i18n'
import { byCode } from '../locales'
import { readStored, writeStored } from '../storage'
import { get } from './api'
import { ADMIN_LOCALES, loadAdminMessages } from './i18n'
import { homeForStage, onSessionExpired, session } from './session'
import type { Role, SessionState } from './types'

const LOCALE_KEY = 'north.admin.locale'

function adminLocaleCode(): string {
  const stored = readStored(LOCALE_KEY)
  if (stored && ADMIN_LOCALES.some((l) => l.code === stored)) return stored
  return preferredLocale().code === 'pt-BR' ? 'pt-BR' : 'en'
}

export async function useAdminLocale(code?: string): Promise<void> {
  const chosen = code ?? adminLocaleCode()
  if (code) writeStored(LOCALE_KEY, code)
  const info = byCode(chosen)
  if (info && i18n.global.locale.value !== chosen) await setLocale(info)
  await loadAdminMessages()
}

export async function loadSession(): Promise<void> {
  try {
    session.set(await get<SessionState>('/auth/me'))
  } catch {
    session.clear()
  }
}

export async function adminGuard(to: RouteLocationNormalized): Promise<true | RouteLocationRaw> {
  await useAdminLocale()
  if (!session.loaded) await loadSession()
  const stage = session.stage
  const home = homeForStage(stage)
  if (to.name === 'admin-login') return stage === null || stage === 'totp' ? true : home
  if (to.name === 'admin-setup') {
    return stage === 'change_password' || stage === 'enroll_totp' ? true : home
  }
  if (stage !== 'ok') return home
  const minRole = to.meta.minRole as Role | undefined
  if (minRole && !session.can(minRole)) return '/admin'
  return true
}

export function installAdminExpiry(router: Router): void {
  onSessionExpired(() => {
    if (router.currentRoute.value.meta.admin) void router.push('/admin/login')
  })
}
