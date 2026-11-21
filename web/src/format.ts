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
