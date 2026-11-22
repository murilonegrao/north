import { i18n } from '../i18n'

export function dateTime(value: string | null | undefined): string {
  if (!value) return i18n.global.t('admin.common.never')
  return new Intl.DateTimeFormat(String(i18n.global.locale.value), {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function duration(start: string | null, end: string | null): string {
  if (!start) return i18n.global.t('admin.common.none')
  const ms = (end ? new Date(end) : new Date()).getTime() - new Date(start).getTime()
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s} s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m} min ${s % 60} s`
  return `${Math.floor(m / 60)} h ${m % 60} min`
}

export function count(n: number | undefined): string {
  return new Intl.NumberFormat(String(i18n.global.locale.value)).format(n ?? 0)
}

/** Job parameters on one line; long values (hashes, stored names) are shortened. */
export function params(p: Record<string, unknown>): string {
  return Object.entries(p)
    .filter(([k]) => k !== 'by')
    .map(([k, v]) => {
      const s = String(v)
      return `${k}=${s.length > 28 ? `${s.slice(0, 12)}…${s.slice(-12)}` : s}`
    })
    .join(' ')
}

/** Job kind title and description in the UI language, the server's English otherwise. */
export function kindText(name: string, field: 'title' | 'description', fallback: string): string {
  const key = `admin.kinds.${name.replace(/\./g, '_')}.${field}`
  return i18n.global.te(key) || i18n.global.te(key, 'en') ? i18n.global.t(key) : fallback
}
