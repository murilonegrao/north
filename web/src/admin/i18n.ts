// Admin strings live outside the public locale files: the admin is an internal tool, offered
// in English and Brazilian Portuguese only (record 0006/X7). Other UI languages fall back to
// English through vue-i18n's fallbackLocale.
import { i18n } from '../i18n'

type Messages = Record<string, unknown>

const loaders = import.meta.glob<Messages>('./locales/*.json', { import: 'default' })
const loaded = new Set<string>()

async function load(code: string): Promise<void> {
  if (loaded.has(code)) return
  const loader = loaders[`./locales/${code}.json`]
  if (!loader) return
  const { _meta: _ignored, ...messages } = await loader()
  i18n.global.mergeLocaleMessage(code, { admin: messages } as never)
  loaded.add(code)
}

export const ADMIN_LOCALES = [
  { code: 'en', name: 'English' },
  { code: 'pt-BR', name: 'Português (Brasil)' },
] as const

/** English always (the fallback), plus the current UI language when the admin has it. */
export async function loadAdminMessages(): Promise<void> {
  await load('en')
  await load(String(i18n.global.locale.value))
}
