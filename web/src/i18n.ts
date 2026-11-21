import { createI18n, type LocaleMessageValue, type VueMessageType } from 'vue-i18n'
import en from './locales/en.json'
import { byCode, type LocaleInfo, LOCALES, matchBrowserLanguage, SOURCE_LOCALE } from './locales'
import { readStored, writeStored } from './storage'

type Messages = Record<string, LocaleMessageValue<VueMessageType>>

/** Drop reviewer metadata such as "_meta": {"machine_translated": true}. */
function stripMeta(messages: Messages): Messages {
  const { _meta: _ignored, ...rest } = messages
  return rest
}

export const i18n = createI18n({
  legacy: false,
  locale: SOURCE_LOCALE.code,
  fallbackLocale: SOURCE_LOCALE.code,
  messages: { [SOURCE_LOCALE.code]: stripMeta(en) },
  missingWarn: import.meta.env.DEV,
  fallbackWarn: false,
})

// Every other locale is a separate chunk, loaded on first use.
const loaders = import.meta.glob<Messages>(['./locales/*.json', '!./locales/en.json'], {
  import: 'default',
})

const STORAGE_KEY = 'north.locale'

export async function setLocale(locale: LocaleInfo): Promise<void> {
  const global = i18n.global
  if (!global.availableLocales.includes(locale.code)) {
    const load = loaders[`./locales/${locale.code}.json`]
    if (load) global.setLocaleMessage(locale.code, stripMeta(await load()))
  }
  global.locale.value = locale.code
  document.documentElement.lang = locale.code
  document.documentElement.dir = locale.dir
}

export function rememberLocale(locale: LocaleInfo): void {
  writeStored(STORAGE_KEY, locale.code)
}

/** Stored choice, else the first browser language we support, else English. */
export function preferredLocale(): LocaleInfo {
  const stored = byCode(readStored(STORAGE_KEY) ?? undefined)
  if (stored) return stored
  for (const tag of navigator.languages ?? [navigator.language]) {
    const match = matchBrowserLanguage(tag)
    if (match) return match
  }
  return SOURCE_LOCALE
}

export { LOCALES }
