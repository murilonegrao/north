// Placement test scoring (record 0008, FR-29, BR-19, BR-20). Pure functions, no I/O:
// the result is computed and kept in the browser and never sent to the server.

export const BANDS = ['A2', 'B1', 'B2', 'C1'] as const
export type Band = (typeof BANDS)[number]
/** A band the test can report: 'below_A2' when even A2 is not reached. */
export type Level = Band | 'below_A2'
export type Skill = 'grammar' | 'vocabulary' | 'reading' | 'listening'

const ORDER: Level[] = ['below_A2', ...BANDS]
/** Share of a band's items that must be right to pass it. */
export const PASS_SHARE = 0.7

export interface Tally {
  correct: number
  total: number
}

/**
 * The band of one skill: the highest band with at least 70% right whose lower bands all have
 * at least 70% too. A band with no items does not stop the climb, but cannot be reached itself.
 */
export function skillBand(tallies: Partial<Record<Band, Tally>>): Level {
  let level: Level = 'below_A2'
  for (const band of BANDS) {
    const t = tallies[band]
    if (!t || t.total === 0) continue
    if (t.correct / t.total < PASS_SHARE) break
    level = band
  }
  return level
}

/** Median of the skill levels; with an even count, the lower of the two middle ones. */
export function overallLevel(levels: Level[]): Level {
  if (levels.length === 0) throw new Error('no skill levels')
  const sorted = [...levels].sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b))
  return sorted[Math.floor((sorted.length - 1) / 2)] as Level
}

export interface Answerable {
  id: string
  band: Band
  answer: number
}

/** Count right answers per band. Unanswered items count as wrong. */
export function tally(items: Answerable[], answers: Record<string, number | undefined>): Partial<Record<Band, Tally>> {
  const out: Partial<Record<Band, Tally>> = {}
  for (const item of items) {
    const t = (out[item.band] ??= { correct: 0, total: 0 })
    t.total += 1
    if (answers[item.id] === item.answer) t.correct += 1
  }
  return out
}

// ---- Official test ranges (BR-20) ----

export type Section = 'overall' | 'reading' | 'listening'

export interface MappingRow {
  test: string
  scale: string
  section: Section
  cefr: Level | 'A1' | 'C2'
  min: number | null
  max: number | null
  note: string
  sourceUrl: string
  checkedOn: string
}

/** The 0–120 TOEFL scale is shown as secondary until this date (record 0008/T19). */
export const TOEFL_LEGACY_END = '2028-01-31'

function splitCsvLine(line: string): string[] {
  const out: string[] = []
  let field = ''
  let quoted = false
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (quoted) {
      if (c === '"' && line[i + 1] === '"') { field += '"'; i++ }
      else if (c === '"') quoted = false
      else field += c
    } else if (c === '"') quoted = true
    else if (c === ',') { out.push(field); field = '' }
    else field += c
  }
  out.push(field)
  return out
}

/** Parse data/reference/cefr_test_mappings.csv. */
export function parseMappings(csv: string): MappingRow[] {
  const [header = '', ...lines] = csv.trim().split(/\r?\n/)
  const cols = splitCsvLine(header)
  const at = (row: string[], name: string) => row[cols.indexOf(name)] ?? ''
  const num = (s: string) => (s === '' ? null : Number(s))
  return lines.filter((l) => l.trim()).map((line) => {
    const r = splitCsvLine(line)
    return {
      test: at(r, 'test'),
      scale: at(r, 'scale'),
      section: at(r, 'section') as Section,
      cefr: at(r, 'cefr') as MappingRow['cefr'],
      min: num(at(r, 'min')),
      max: num(at(r, 'max')),
      note: at(r, 'note'),
      sourceUrl: at(r, 'source_url'),
      checkedOn: at(r, 'checked_on'),
    }
  })
}

/**
 * The official ranges for a level and section. 'below_A2' maps to A1 rows only (tests that
 * publish A1). The TOEFL 0–120 rows are dropped from `today` on, after TOEFL_LEGACY_END.
 */
export function rangesFor(rows: MappingRow[], level: Level, section: Section, today: string): MappingRow[] {
  const cefr = level === 'below_A2' ? 'A1' : level
  return rows.filter(
    (r) =>
      r.cefr === cefr &&
      r.section === section &&
      !(r.scale === 'ibt_0_120' && today > TOEFL_LEGACY_END),
  )
}
