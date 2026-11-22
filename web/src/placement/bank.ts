// The placement item bank (record 0008/T21): YAML in data/placement/items, parsed at build
// time by the north-yaml Vite plugin, and the official CEFR test tables (BR-20).
import grammar from '../../../data/placement/items/grammar.yaml'
import vocabulary from '../../../data/placement/items/vocabulary.yaml'
import mappingsCsv from '../../../data/reference/cefr_test_mappings.csv?raw'
import { parseMappings, type Band, type MappingRow, type Skill } from './score'

export interface Passage {
  id: string
  band: Band
  title: string
  text: string
  audio_file?: string
  voice?: string
  speed?: number
}

export interface Item {
  id: string
  band: Band
  passage?: string
  prompt: string
  options: string[]
  answer: number
  explanation: string
}

export interface SkillFile {
  bank_version: string
  skill: Skill
  passages?: Passage[]
  items: Item[]
}

/** Skills in the order the test presents them. Reading and listening join when written. */
export const SECTIONS: SkillFile[] = [grammar as SkillFile, vocabulary as SkillFile]

export const BANK_VERSION = (grammar as SkillFile).bank_version

export const MAPPINGS: MappingRow[] = parseMappings(mappingsCsv)
