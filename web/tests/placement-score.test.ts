import { describe, expect, it } from 'vitest'
import { BANK_VERSION, MAPPINGS, SECTIONS } from '../src/placement/bank'
import { overallLevel, rangesFor, skillBand, tally, TOEFL_LEGACY_END } from '../src/placement/score'

describe('skillBand (FR-29)', () => {
  it('climbs while every band has at least 70% right', () => {
    expect(skillBand({ A2: { correct: 5, total: 5 }, B1: { correct: 4, total: 5 }, B2: { correct: 2, total: 4 } })).toBe('B1')
  })

  it('a lower band under 70% caps the level, even if a higher band passes', () => {
    expect(skillBand({ A2: { correct: 5, total: 5 }, B1: { correct: 3, total: 5 }, B2: { correct: 4, total: 5 } })).toBe('A2')
  })

  it('reports below_A2 when A2 is not reached', () => {
    expect(skillBand({ A2: { correct: 2, total: 5 }, B1: { correct: 5, total: 5 } })).toBe('below_A2')
  })

  it('70% exactly passes; 69% does not', () => {
    expect(skillBand({ A2: { correct: 7, total: 10 } })).toBe('A2')
    expect(skillBand({ A2: { correct: 69, total: 100 } })).toBe('below_A2')
  })

  it('reaches C1 with every band passed', () => {
    const all = { correct: 4, total: 4 }
    expect(skillBand({ A2: all, B1: all, B2: all, C1: all })).toBe('C1')
  })
})

describe('overallLevel', () => {
  it('takes the lower middle with an even count', () => {
    expect(overallLevel(['B1', 'B2', 'B2', 'B1'])).toBe('B1')
  })

  it('takes the middle with an odd count, whatever the order', () => {
    expect(overallLevel(['C1', 'A2', 'B2'])).toBe('B2')
  })
})

describe('tally', () => {
  it('counts unanswered items as wrong', () => {
    const items = [
      { id: 'a', band: 'A2' as const, answer: 1 },
      { id: 'b', band: 'A2' as const, answer: 0 },
      { id: 'c', band: 'B1' as const, answer: 2 },
    ]
    expect(tally(items, { a: 1, c: 0 })).toEqual({ A2: { correct: 1, total: 2 }, B1: { correct: 0, total: 1 } })
  })
})

describe('official ranges (BR-20)', () => {
  it('gives the IELTS range for B1 from the mapping file, with a source', () => {
    const ielts = rangesFor(MAPPINGS, 'B1', 'overall', '2026-11-22').find((r) => r.test === 'ielts_academic')
    expect(ielts).toMatchObject({ min: 4, max: 5 })
    expect(ielts?.sourceUrl).toMatch(/^https:\/\/ielts\.org\//)
  })

  it('has no per-skill IELTS range, because IELTS does not publish one', () => {
    expect(rangesFor(MAPPINGS, 'B2', 'listening', '2026-11-22').some((r) => r.test === 'ielts_academic')).toBe(false)
  })

  it('has per-skill TOEFL and Cambridge ranges', () => {
    const tests = rangesFor(MAPPINGS, 'B2', 'reading', '2026-11-22').map((r) => r.test)
    expect(tests).toEqual(expect.arrayContaining(['toefl_ibt', 'cambridge']))
  })

  it('drops the TOEFL 0–120 scale after 2028-01-31', () => {
    const scales = (day: string) => rangesFor(MAPPINGS, 'B2', 'overall', day).filter((r) => r.test === 'toefl_ibt').map((r) => r.scale)
    expect(scales(TOEFL_LEGACY_END)).toEqual(expect.arrayContaining(['ibt_1_6', 'ibt_0_120']))
    expect(scales('2028-02-01')).toEqual(['ibt_1_6'])
  })

  it('covers all seven tests at B2', () => {
    const tests = new Set(rangesFor(MAPPINGS, 'B2', 'overall', '2026-11-22').map((r) => r.test))
    expect([...tests].sort()).toEqual(['cambridge', 'duolingo', 'ielts_academic', 'languagecert', 'pte_academic', 'toefl_ibt', 'trinity_ise'])
  })

  it('every row cites an https source and a check date', () => {
    for (const r of MAPPINGS) {
      expect(r.sourceUrl).toMatch(/^https:\/\//)
      expect(r.checkedOn).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    }
  })
})

describe('item bank', () => {
  it('loads every section with one bank version', () => {
    expect(SECTIONS.map((s) => s.skill)).toEqual(['grammar', 'vocabulary'])
    expect(new Set(SECTIONS.map((s) => s.bank_version))).toEqual(new Set([BANK_VERSION]))
  })

  it('a perfect run reaches C1 in every section', () => {
    for (const s of SECTIONS) {
      const answers = Object.fromEntries(s.items.map((i) => [i.id, i.answer]))
      expect(skillBand(tally(s.items, answers))).toBe('C1')
    }
  })
})
