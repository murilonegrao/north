// Numbers, money and dates in the viewer's locale (NFR-14). Program data itself stays in English.
import type { Money } from './api/types'

export function formatNumber(value: number, locale: string): string {
  return new Intl.NumberFormat(locale).format(value)
}

export function formatMoney(money: Money, locale: string): string {
  return new Intl.NumberFormat(locale, { style: 'currency', currency: money.currency, maximumFractionDigits: 0 }).format(money.amount)
}

/** `2026-11-21` or a full timestamp; date-only values are read as calendar dates (no timezone shift). */
export function formatDate(value: string, locale: string): string {
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value)
  const date = new Date(dateOnly ? `${value}T00:00:00Z` : value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeZone: dateOnly ? 'UTC' : undefined }).format(date)
}

/** i18n keys cannot contain dots: `admissions.english` → `admissions_english`, `30.70` → `30_70`. */
export function keyOf(id: string): string {
  return id.replace(/\./g, '_')
}

/** The URL itself when it is a web address (http: or https:), else null: data never becomes a
 * `javascript:` or `data:` link. */
export function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const { protocol } = new URL(value)
    return protocol === 'http:' || protocol === 'https:' ? value : null
  } catch {
    return null
  }
}

/** "Austin, TX", or just "TX" when the city is unknown (never ", TX"). */
export function placeLabel(city: string | null | undefined, state: string): string {
  return city ? `${city}, ${state}` : state
}
