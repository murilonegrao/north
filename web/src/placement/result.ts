// Placement results kept in the browser only (BR-19, FR-35): a short history for the monthly
// retake, exportable as JSON. Nothing here is sent to the server.
import { readStored, writeStored } from '../storage'
import type { Level, Skill } from './score'

export interface PlacementResult {
  taken_at: string
  bank_version: string
  bands: Partial<Record<Skill, Level>>
  overall: Level
}

const KEY = 'north.placement.results'
const KEEP = 24

export function loadResults(): PlacementResult[] {
  try {
    const parsed: unknown = JSON.parse(readStored(KEY) ?? '[]')
    return Array.isArray(parsed) ? (parsed as PlacementResult[]) : []
  } catch {
    return []
  }
}

export function saveResult(result: PlacementResult): PlacementResult[] {
  const all = [...loadResults(), result].slice(-KEEP)
  writeStored(KEY, JSON.stringify(all))
  return all
}

/** Display names of the tests: proper names, not translated. */
export const TEST_NAMES: Record<string, string> = {
  ielts_academic: 'IELTS Academic',
  toefl_ibt: 'TOEFL iBT',
  cambridge: 'Cambridge English Scale',
  duolingo: 'Duolingo English Test',
  pte_academic: 'PTE Academic',
  languagecert: 'LanguageCert Academic',
  trinity_ise: 'Trinity ISE',
}
