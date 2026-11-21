/** Wave-1 UI languages (NFR-14). English is the source and the fallback. */
export interface LocaleInfo {
  /** BCP 47 tag, used for vue-i18n, <html lang> and the locale file name. */
  code: string
  /** URL prefix segment (lowercase). */
  prefix: string
  /** Writing direction; 'rtl' arrives with Arabic in wave 2. */
  dir: 'ltr' | 'rtl'
  /** Endonym shown in the language switcher. */
  name: string
}

export const LOCALES: readonly LocaleInfo[] = [
  { code: 'en', prefix: 'en', dir: 'ltr', name: 'English' },
  { code: 'es', prefix: 'es', dir: 'ltr', name: 'Español' },
  { code: 'pt-BR', prefix: 'pt-br', dir: 'ltr', name: 'Português (Brasil)' },
  { code: 'zh-Hans', prefix: 'zh-hans', dir: 'ltr', name: '简体中文' },
]

export const SOURCE_LOCALE = LOCALES[0]!

export function byPrefix(prefix: string | undefined): LocaleInfo | undefined {
  return LOCALES.find((l) => l.prefix === prefix?.toLowerCase())
}

export function byCode(code: string | undefined): LocaleInfo | undefined {
  return LOCALES.find((l) => l.code === code)
}

/** Map a browser language tag (navigator.languages) to a wave-1 locale. */
export function matchBrowserLanguage(tag: string): LocaleInfo | undefined {
  const lower = tag.toLowerCase()
  const primary = lower.split('-')[0]
  if (primary === 'pt') return byCode('pt-BR')
  if (primary === 'zh') return byCode('zh-Hans')
  return LOCALES.find((l) => l.code.toLowerCase() === primary)
}
