<script setup lang="ts">
// One English course (record 0008, slice E2; FR-17): every value with its status, source and
// date; what the lists do not carry (price, start dates) is listed as not collected yet.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ApiError, getCourse } from '../api/client'
import type { CourseDetail } from '../api/types'
import StatusBadge from '../components/StatusBadge.vue'
import StatusLegend from '../components/StatusLegend.vue'
import VerifiedField from '../components/VerifiedField.vue'
import { EXAM_NAMES, LIST_NAMES } from '../courses'
import { formatDate, formatNumber, keyOf, safeHttpUrl } from '../format'
import { useLocalePrefix } from '../programs'

const { t, te, locale } = useI18n()
const route = useRoute()
const prefix = useLocalePrefix()

type Load = { state: 'loading' } | { state: 'not_found' } | { state: 'error' } | { state: 'ok'; data: CourseDetail }
const load = ref<Load>({ state: 'loading' })
let controller: AbortController | undefined
const id = computed(() => String(route.params.id ?? ''))

async function fetchCourse() {
  controller?.abort()
  controller = new AbortController()
  const signal = controller.signal
  load.value = { state: 'loading' }
  try {
    const data = await getCourse(id.value, signal)
    if (signal.aborted) return
    // A degree program id opened here: not a course page.
    load.value = data.kind === 'language_course' ? { state: 'ok', data } : { state: 'not_found' }
  } catch (error) {
    if (signal.aborted) return
    load.value = error instanceof ApiError && error.status === 404 ? { state: 'not_found' } : { state: 'error' }
  }
}
watch(id, fetchCourse, { immediate: true })
onBeforeUnmount(() => controller?.abort())

const course = computed(() => (load.value.state === 'ok' ? load.value.data : null))

function setPageMeta() {
  const c = course.value
  if (!c) return
  document.title = t('courses.detail.pageTitle', { title: c.title, provider: c.institution.name })
  document.querySelector('meta[name="description"]')?.setAttribute('content', t('courses.pageDescription'))
}
watch([course, locale, () => route.fullPath], setPageMeta, { flush: 'post' })

const num = (n: number) => formatNumber(n, locale.value)
const date = (value: string) => formatDate(value, locale.value)
const known = (v: { value: unknown; status: string }): boolean => v.status !== 'unknown' && v.value !== null
const examName = (exam: string) => (exam === 'other' ? t('courses.values.examOther') : EXAM_NAMES[exam as keyof typeof EXAM_NAMES] ?? exam)
const listName = (scheme: string) => LIST_NAMES[scheme] ?? scheme
function notCollectedLabel(field: string): string {
  const key = `detail.notCollectedFields.${keyOf(field)}`
  return te(key) ? t(key) : field
}
function sourceName(source: string): string {
  const key = `detail.sourceNames.${keyOf(source)}`
  return te(key) ? t(key) : source
}
function noteText(code: string): string {
  const key = `courses.notes.${keyOf(code)}`
  return te(key) ? t(key) : code
}
function sourceFileText(source: { file_version: string; uploaded_at: string; rows: number | null }): string {
  const params = { version: source.file_version, date: date(source.uploaded_at) }
  return source.rows === null ? t('detail.sourceFileNoRows', params) : t('detail.sourceFile', { ...params, rows: num(source.rows) })
}
</script>

<template>
  <p class="back">
    <RouterLink :to="`/${prefix}/english-courses`">{{ t('courses.detail.back') }}</RouterLink>
  </p>

  <p v-if="load.state === 'loading'" class="state-message" aria-live="polite">{{ t('detail.loading') }}</p>

  <div v-else-if="load.state === 'not_found'" class="state-message card" role="alert">
    <h1>{{ t('courses.detail.notFound') }}</h1>
  </div>

  <div v-else-if="load.state === 'error'" class="state-message card" role="alert">
    <p>{{ t('detail.error') }}</p>
    <button type="button" class="button-quiet" @click="fetchCourse">{{ t('programs.retry') }}</button>
  </div>

  <article v-else-if="course" aria-labelledby="course-title">
    <header class="course-header">
      <p class="eyebrow">{{ t('courses.eyebrow') }}</p>
      <h1 id="course-title">{{ course.title }}</h1>
      <p class="where">
        {{ course.institution.name }} ·
        <template v-if="course.campus.city">{{ course.campus.city }}</template>
        <span v-else class="muted">{{ t('courses.values.cityUnknown') }}</span>
      </p>
    </header>

    <StatusLegend class="legend-block" />

    <section aria-labelledby="lists-heading" class="card section">
      <h2 id="lists-heading">{{ t('courses.detail.sections.lists') }}</h2>
      <dl>
        <VerifiedField
          :label="t('courses.fields.authorization')"
          :status="course.intl_authorization.status"
          :source-url="course.intl_authorization.source_url"
          :verified-at="course.intl_authorization.verified_at"
          :evidence="course.intl_authorization.evidence"
        >
          <template v-if="course.intl_authorization.value">{{ listName(course.intl_authorization.value.scheme) }}</template>
          <span v-else class="muted">{{ t('courses.values.notFound') }}</span>
          <template #note>
            <p v-for="note in course.intl_authorization.notes" :key="note.code" class="note notice" data-test="rule-note">
              {{ noteText(note.code) }}
              <a v-if="safeHttpUrl(note.source_url)" :href="note.source_url" target="_blank" rel="noopener noreferrer">
                {{ t('detail.meta.source') }}<span class="visually-hidden"> ({{ t('detail.meta.newTab') }})</span>
              </a>
              <span class="muted"> · {{ t('detail.meta.checked', { date: date(note.checked_on) }) }}</span>
            </p>
          </template>
        </VerifiedField>

        <VerifiedField
          v-for="key in (['exam', 'cefr_entry', 'cefr_exit', 'weeks', 'hours_per_week'] as const)"
          :key="key"
          :label="t(`courses.fields.${key}`)"
          :status="course.language_course[key].status"
          :source-url="course.language_course[key].source_url"
          :verified-at="course.language_course[key].verified_at"
          :evidence="course.language_course[key].evidence"
        >
          <template v-if="known(course.language_course[key])">
            <template v-if="key === 'exam'">{{ examName(String(course.language_course.exam.value)) }}</template>
            <template v-else-if="key === 'weeks'">{{ t('courses.values.weeks', { n: num(Number(course.language_course.weeks.value)) }) }}</template>
            <template v-else-if="key === 'hours_per_week'">{{ t('courses.values.hours', { n: num(Number(course.language_course.hours_per_week.value)) }) }}</template>
            <template v-else>{{ course.language_course[key].value }}</template>
          </template>
          <span v-else class="muted">{{ t('courses.values.unknown') }}</span>
        </VerifiedField>
      </dl>
    </section>

    <section aria-labelledby="missing-heading" class="card section not-collected" data-test="not-collected">
      <h2 id="missing-heading">
        <StatusBadge status="unknown" />
        {{ t('detail.sections.notCollected') }}
      </h2>
      <p class="section-intro">{{ t('courses.detail.notCollectedIntro') }}</p>
      <ul>
        <li v-for="field in course.not_yet_collected" :key="field">{{ notCollectedLabel(field) }}</li>
      </ul>
    </section>

    <section aria-labelledby="facts-heading" class="card section">
      <h2 id="facts-heading">{{ t('detail.sections.facts') }}</h2>
      <dl class="facts">
        <div>
          <dt>{{ t('courses.fields.provider') }}</dt>
          <dd>{{ course.institution.name }}</dd>
        </div>
        <div v-if="course.campus.locality">
          <dt>{{ t('courses.fields.county') }}</dt>
          <dd>{{ course.campus.locality.name }}</dd>
        </div>
        <div>
          <dt>{{ t('detail.fields.identifiers') }}</dt>
          <dd>
            <span v-for="(value, key) in course.institution.identifiers" :key="key" class="identifier">
              {{ t(`courses.identifiers.${key}`) }} <code>{{ value }}</code>
            </span>
            <span v-for="ident in course.identifiers" :key="`${ident.scheme}-${ident.value}`" class="identifier">
              {{ t(`courses.identifiers.${ident.scheme}`) }} <code>{{ ident.value }}</code>
            </span>
          </dd>
        </div>
      </dl>
    </section>

    <section aria-labelledby="sources-heading" class="card section">
      <h2 id="sources-heading">{{ t('detail.sections.sources') }}</h2>
      <p class="section-intro">{{ t('detail.sourcesIntro') }}</p>
      <ul class="sources">
        <li v-for="source in course.sources" :key="`${source.source}-${source.file_version}`">
          <span class="source-name">{{ sourceName(source.source) }}</span>
          <span class="muted">{{ sourceFileText(source) }}</span>
          <code class="sha" :title="source.sha256">SHA-256 {{ source.sha256.slice(0, 12) }}…</code>
        </li>
      </ul>
    </section>
  </article>
</template>

<style scoped>
.back {
  margin-block: 0 1rem;
  font-family: var(--font-mono);
  font-size: 0.875rem;
}
.course-header {
  margin-block-end: 1.25rem;
}
h1 {
  margin-block: 0.25rem 0.375rem;
  font-size: clamp(1.5rem, 5vw, 2.125rem);
  overflow-wrap: anywhere;
}
.where {
  margin-block: 0;
  color: var(--text-muted);
}
.legend-block {
  margin-block-end: 1.25rem;
}
.section {
  margin-block-end: 1.25rem;
}
h2 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-block: 0 0.5rem;
  font-size: 1rem;
}
dl {
  margin: 0;
}
.note {
  margin-block: 0.25rem 0;
  font-size: 0.8125rem;
}
.notice {
  padding-inline-start: 0.75rem;
  border-inline-start: 2px solid var(--accent-dim);
}
.muted {
  color: var(--text-muted);
}
.section-intro {
  margin-block: 0 0.75rem;
  font-size: 0.9375rem;
  color: var(--text-muted);
}
.not-collected {
  border-style: dotted;
}
.not-collected ul {
  margin: 0;
  padding-inline-start: 1.25rem;
}
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
  gap: 0.75rem 1.5rem;
}
.facts dt {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}
.facts dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.identifier {
  margin-inline-end: 1rem;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}
.sources {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}
.sources li {
  display: flex;
  flex-wrap: wrap;
  gap: 0.125rem 0.75rem;
  font-size: 0.875rem;
}
.source-name {
  font-weight: 500;
}
.sha {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.state-message {
  color: var(--text-muted);
}
.button-quiet {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding-block: 0.375rem;
  padding-inline: 0.75rem;
  cursor: pointer;
}
</style>
