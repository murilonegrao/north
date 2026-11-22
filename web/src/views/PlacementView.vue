<script setup lang="ts">
// English placement test v0 (record 0008, FR-28, FR-29, FR-35). Runs fully in the browser:
// the answers and the result never leave it (BR-19).
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { BANK_VERSION, MAPPINGS, SECTIONS, type Item } from '../placement/bank'
import { loadResults, saveResult, TEST_NAMES, type PlacementResult } from '../placement/result'
import { overallLevel, rangesFor, skillBand, tally, type Level, type MappingRow, type Section, type Skill } from '../placement/score'

const { t } = useI18n()

type Phase = 'intro' | 'test' | 'result'
const phase = ref<Phase>('intro')
const answers = ref<Record<string, number | undefined>>({})
const position = ref(0)
const result = ref<PlacementResult | null>(null)
const previous = ref<PlacementResult | null>(null)
const questionHeading = ref<HTMLElement | null>(null)

interface Step { skill: Skill; item: Item }
const steps: Step[] = SECTIONS.flatMap((s) => s.items.map((item) => ({ skill: s.skill, item })))
// position stays within 0 .. steps.length - 1
const step = computed(() => steps[position.value] as Step)
const chosen = computed(() => answers.value[step.value.item.id])
const sectionIndex = computed(() => SECTIONS.findIndex((s) => s.skill === step.value.skill))
const minutes = Math.ceil(steps.length * 0.4)

function start() {
  answers.value = {}
  position.value = 0
  result.value = null
  phase.value = 'test'
  focusQuestion()
}

function focusQuestion() {
  void nextTick(() => questionHeading.value?.focus())
}

function choose(index: number) {
  answers.value = { ...answers.value, [step.value.item.id]: index }
}

function next() {
  if (position.value < steps.length - 1) {
    position.value += 1
    focusQuestion()
  } else finish()
}

function back() {
  if (position.value > 0) {
    position.value -= 1
    focusQuestion()
  }
}

function finish() {
  const bands: Partial<Record<Skill, Level>> = {}
  for (const s of SECTIONS) bands[s.skill] = skillBand(tally(s.items, answers.value))
  const history = loadResults()
  previous.value = history.at(-1) ?? null
  result.value = {
    taken_at: new Date().toISOString(),
    bank_version: BANK_VERSION,
    bands,
    overall: overallLevel(Object.values(bands) as Level[]),
  }
  saveResult(result.value)
  phase.value = 'result'
  window.scrollTo({ top: 0 })
}

const today = new Date().toISOString().slice(0, 10)

/** Ranges grouped by test for one section, in a stable order. */
function rangesByTest(level: Level, section: Section): { test: string; rows: MappingRow[] }[] {
  const rows = rangesFor(MAPPINGS, level, section, today)
  return Object.keys(TEST_NAMES)
    .map((test) => ({ test, rows: rows.filter((r) => r.test === test) }))
    .filter((g) => g.rows.length > 0)
}

function rangeText(r: MappingRow): string {
  if (r.min === null) return r.note
  const span = r.min === r.max ? String(r.min) : `${r.min}–${r.max}`
  return r.scale === 'ibt_0_120' ? t('placement.legacyScale', { span }) : span
}

function levelLabel(level: Level | undefined): string {
  return level === undefined ? '—' : level === 'below_A2' ? t('placement.belowA2') : level
}

const ORDER: Level[] = ['below_A2', 'A2', 'B1', 'B2', 'C1']
function change(skill: Skill): string {
  const now = result.value?.bands[skill]
  const before = previous.value?.bands[skill]
  if (!now || !before) return ''
  const d = ORDER.indexOf(now) - ORDER.indexOf(before)
  return d > 0 ? t('placement.up', { level: levelLabel(before) }) : d < 0 ? t('placement.down', { level: levelLabel(before) }) : t('placement.same')
}

function exportJson() {
  if (!result.value) return
  const blob = new Blob([JSON.stringify(loadResults(), null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'north-placement-results.json'
  a.click()
  URL.revokeObjectURL(url)
}

const review = computed(() => steps.filter((s) => answers.value[s.item.id] !== s.item.answer))
</script>

<template>
  <section v-if="phase === 'intro'" class="intro" aria-labelledby="placement-title">
    <p class="eyebrow">{{ t('placement.eyebrow') }}</p>
    <h1 id="placement-title">{{ t('placement.title') }}</h1>
    <p class="lead">{{ t('placement.lead', { count: steps.length, minutes }) }}</p>
    <ul class="facts">
      <li>{{ t('placement.factSkills') }}</li>
      <li>{{ t('placement.factEstimate') }}</li>
      <li>{{ t('placement.factPrivate') }}</li>
    </ul>
    <button type="button" class="primary" @click="start">{{ t('placement.start') }}</button>
  </section>

  <section v-else-if="phase === 'test'" class="test" aria-labelledby="question">
    <div class="progress">
      <span class="eyebrow">{{ t(`placement.skill.${step.skill}`) }} · {{ t('placement.sectionOf', { n: sectionIndex + 1, total: SECTIONS.length }) }}</span>
      <span class="count">{{ t('placement.questionOf', { n: position + 1, total: steps.length }) }}</span>
      <div class="bar" role="progressbar" :aria-valuenow="position + 1" aria-valuemin="1" :aria-valuemax="steps.length" :aria-label="t('placement.progress')">
        <i :style="{ inlineSize: `${((position + 1) / steps.length) * 100}%` }"></i>
      </div>
    </div>
    <h2 id="question" ref="questionHeading" tabindex="-1" class="prompt" lang="en">{{ step.item.prompt }}</h2>
    <fieldset class="options">
      <legend class="visually-hidden">{{ t('placement.chooseOne') }}</legend>
      <label v-for="(option, i) in step.item.options" :key="`${step.item.id}-${i}`" :class="['option', { selected: chosen === i }]">
        <input type="radio" :name="step.item.id" :value="i" :checked="chosen === i" @change="choose(i)" />
        <span lang="en">{{ option }}</span>
      </label>
    </fieldset>
    <div class="actions">
      <button type="button" :disabled="position === 0" @click="back">{{ t('placement.back') }}</button>
      <button type="button" class="primary" @click="next">
        {{ position === steps.length - 1 ? t('placement.finish') : chosen === undefined ? t('placement.skip') : t('placement.next') }}
      </button>
    </div>
  </section>

  <section v-else-if="result" class="result" aria-labelledby="result-title">
    <p class="eyebrow">{{ t('placement.resultEyebrow') }}</p>
    <h1 id="result-title">{{ t('placement.resultTitle', { level: levelLabel(result.overall) }) }}</h1>
    <p class="label">{{ SECTIONS.length === 4 ? t('placement.resultLabel') : t('placement.resultLabelPartial') }}</p>

    <h2>{{ t('placement.bySkill') }}</h2>
    <dl class="skills">
      <template v-for="s in SECTIONS" :key="s.skill">
        <dt>{{ t(`placement.skill.${s.skill}`) }}</dt>
        <dd><strong>{{ levelLabel(result.bands[s.skill]) }}</strong> <span v-if="change(s.skill)" class="muted">{{ change(s.skill) }}</span></dd>
      </template>
    </dl>

    <h2>{{ t('placement.ranges') }}</h2>
    <p class="muted">{{ t('placement.rangesNote') }}</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th scope="col">{{ t('placement.test') }}</th><th scope="col">{{ t('placement.range') }}</th><th scope="col">{{ t('placement.source') }}</th></tr></thead>
        <tbody>
          <template v-for="g in rangesByTest(result.overall, 'overall')" :key="g.test">
            <tr v-for="(r, i) in g.rows" :key="r.scale">
              <th v-if="i === 0" scope="row" :rowspan="g.rows.length">{{ TEST_NAMES[g.test] }}</th>
              <td>{{ rangeText(r) }}</td>
              <td><a :href="r.sourceUrl" rel="noopener" target="_blank">{{ t('placement.checkedOn', { date: r.checkedOn }) }}</a></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <p v-if="rangesByTest(result.overall, 'overall').length === 0" class="muted">{{ t('placement.noRanges') }}</p>

    <div class="actions">
      <button type="button" class="primary" @click="start">{{ t('placement.retake') }}</button>
      <button type="button" @click="exportJson">{{ t('placement.export') }}</button>
    </div>

    <details v-if="review.length" class="review">
      <summary>{{ t('placement.review', { count: review.length }) }}</summary>
      <ol>
        <li v-for="s in review" :key="s.item.id">
          <p lang="en">{{ s.item.prompt }}</p>
          <p><strong lang="en">{{ s.item.options[s.item.answer] }}</strong> — <span lang="en">{{ s.item.explanation }}</span></p>
        </li>
      </ol>
    </details>
  </section>
</template>

<style scoped>
section { max-inline-size: var(--measure); display: grid; gap: 1rem; }
h1 { margin: 0; font-size: clamp(1.75rem, 5vw, 2.25rem); }
h2 { margin-block: 1rem 0; font-size: 1.125rem; }
.lead, .label { margin: 0; }
.label { color: var(--text-muted); }
.muted { color: var(--text-muted); font-size: 0.875rem; margin: 0; }
.facts { margin: 0; padding-inline-start: 1.25rem; display: grid; gap: 0.25rem; }
button { font: inherit; padding: 0.6rem 1rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
button:disabled { opacity: 0.5; cursor: default; }
button.primary { background: var(--accent); border-color: var(--accent); color: var(--charcoal); font-weight: 600; justify-self: start; }
.progress { display: grid; grid-template-columns: 1fr auto; gap: 0.5rem; align-items: baseline; }
.count { font-family: var(--font-mono); font-size: 0.8125rem; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.bar { grid-column: 1 / -1; block-size: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.bar i { display: block; block-size: 100%; background: var(--accent); }
.prompt { font-family: var(--font-sans); font-size: 1.25rem; font-weight: 500; margin: 0.5rem 0 0; outline: none; }
.options { border: 0; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
.option { display: flex; gap: 0.75rem; align-items: center; padding: 0.75rem 1rem; border: 1px solid var(--border); border-radius: var(--radius); cursor: pointer; }
.option.selected { border-color: var(--accent); }
.option input { accent-color: var(--ember); }
.actions { display: flex; flex-wrap: wrap; gap: 0.75rem; }
.skills { display: grid; grid-template-columns: max-content 1fr; gap: 0.25rem 1.5rem; margin: 0; }
.skills dt { color: var(--text-muted); }
.skills dd { margin: 0; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; inline-size: 100%; font-size: 0.9375rem; }
th, td { text-align: start; padding: 0.5rem 0.75rem 0.5rem 0; border-block-end: 1px solid var(--border); vertical-align: top; }
td { font-variant-numeric: tabular-nums; }
thead th { font-family: var(--font-mono); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); font-weight: 500; }
a { color: var(--accent-text); }
.review ol { display: grid; gap: 0.75rem; padding-inline-start: 1.25rem; }
.review p { margin: 0; }
.visually-hidden { position: absolute; inline-size: 1px; block-size: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
</style>
