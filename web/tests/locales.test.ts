// NFR-14: every key of the source locale (en) exists in every other wave-1 locale.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { LOCALES, SOURCE_LOCALE } from '../src/locales'

type Tree = { [key: string]: string | Tree }

function load(code: string): Tree {
  const url = new URL(`../src/locales/${code}.json`, import.meta.url)
  const { _meta: _ignored, ...messages } = JSON.parse(readFileSync(fileURLToPath(url), 'utf8'))
  return messages as Tree
}

function leaves(tree: Tree, prefix = ''): Map<string, string> {
  const out = new Map<string, string>()
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (typeof value === 'string') out.set(path, value)
    else for (const [k, v] of leaves(value, path)) out.set(k, v)
  }
  return out
}

const source = leaves(load(SOURCE_LOCALE.code))
const others = LOCALES.filter((l) => l !== SOURCE_LOCALE)

describe('locale files', () => {
  it.each(others.map((l) => [l.code]))('%s has every key of en, none empty', (code) => {
    const target = leaves(load(code))
    const missing = [...source.keys()].filter((k) => !target.get(k)?.trim())
    expect(missing).toEqual([])
  })

  it.each(others.map((l) => [l.code]))('%s has no keys unknown to en', (code) => {
    const extra = [...leaves(load(code)).keys()].filter((k) => !source.has(k))
    expect(extra).toEqual([])
  })

  // Each non-source locale says how it was produced: machine translated, or reviewed by a
  // native speaker on a given date. Never the reviewer's name (no personal data).
  it.each(others.map((l) => [l.code]))('%s declares its translation status', (code) => {
    const url = new URL(`../src/locales/${code}.json`, import.meta.url)
    const raw = JSON.parse(readFileSync(fileURLToPath(url), 'utf8'))
    const meta = raw._meta
    if (meta?.machine_translated === true) {
      expect(meta).toEqual({ machine_translated: true })
    } else {
      expect(meta).toEqual({ machine_translated: false, native_review_on: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) })
    }
  })
})
