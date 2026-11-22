<script setup lang="ts">
// English courses in Ireland (record 0008, slice E2; FR-16, FR-35): every course on the Stamp 2
// lists, filtered by city, exam, entry level and hours a week. "Up to my level" reads the last
// placement result kept in this browser (BR-19) and never sends it anywhere but as a filter.
// Price and start dates are not on the lists: they show as unknown, never as a no (BR-02).
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getFacets, listCourses } from '../api/client'
import { CEFR_BANDS, type CourseList, type CourseSummary, EXAMS, type Facets } from '../api/types'
import StatusBadge from '../components/StatusBadge.vue'
import StatusLegend from '../components/StatusLegend.vue'
import {
  activeCourseFilterCount,
  type CourseFilters,
  effectiveLevel,
  EXAM_NAMES,
  HOURS_OPTIONS,
  LIST_NAMES,
  parseCourseFilters,
  placementBand,
  toCourseApiQuery,
  toCourseUrlQuery,
} from '../courses'
import { formatMoney, formatNumber } from '../format'
import { loadResults } from '../placement/result'
import { useLocalePrefix } from '../programs'

const PAGE_SIZE = 25

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const prefix = useLocalePrefix()

const filters = computed(() => parseCourseFilters(route.query))
const activeCount = computed(() => activeCourseFilterCount(filters.value))
// The last placement result in this browser (BR-19): its overall band, if any.
const myBand = placementBand(loadResults().at(-1) ?? null)
const level = computed(() => effectiveLevel(filters.value, myBand))

type Load = { state: 'loading' } | { state: 'error' } | { state: 'ok'; data: CourseList }
const load = ref<Load>({ state: 'loading' })
let controller: AbortController | undefined

async function fetchCourses() {
  controller?.abort()
  controller = new AbortController()
  const signal = controller.signal
  load.value = { state: 'loading' }
  try {
    const data = await listCourses(toCourseApiQuery(filters.value, PAGE_SIZE, myBand), signal)
    if (!signal.aborted) load.value = { state: 'ok', data }
  } catch (error) {
    if (!signal.aborted) load.value = { state: 'error' }
    if ((error as Error)?.name !== 'AbortError') console.warn('courses: load failed', error)
  }
}
watch(() => JSON.stringify(toCourseApiQuery(filters.value, PAGE_SIZE, myBand)), fetchCourses, { immediate: true })
onBeforeUnmount(() => controller?.abort())

// Counts next to the options; the list works without them.
const facets = ref<Facets | null>(null)
const facetsController = new AbortController()
getFacets(undefined, facetsController.signal, { country: 'IE', kind: 'language_course' })
  .then((data) => (facets.value = data))
  .catch((error) => {
    if ((error as Error)?.name !== 'AbortError') console.warn('course facets: load failed', error)
  })
onBeforeUnmount(() => facetsController.abort())

function navigate(next: CourseFilters) {
  router.replace({ query: toCourseUrlQuery(next) })
}
function change(changes: Partial<CourseFilters>) {
  navigate({ ...filters.value, ...changes, page: 1 })
}
function clearFilters() {
  navigate({ mine: false, page: 1 })
}
function selectValue(event: Event): string | undefined {
  return (event.target as HTMLSelectElement).value || undefined
}

const pages = computed(() => (load.value.state === 'ok' ? Math.max(1, Math.ceil(load.value.data.total / PAGE_SIZE)) : 1))
function pageLink(n: number) {
  return { query: { ...route.query, page: n > 1 ? String(n) : undefined } }
}

const num = (n: number) => formatNumber(n, locale.value)
const withCount = (label: string, n: number | undefined) => (n === undefined ? label : `${label} (${num(n)})`)
const examName = (exam: string) => (exam === 'other' ? t('courses.values.examOther') : EXAM_NAMES[exam as keyof typeof EXAM_NAMES] ?? exam)
const listName = (scheme: string) => LIST_NAMES[scheme] ?? scheme
const filtersOpen = ref(false)

function known<T>(v: { value: T | null; status: string }): v is { value: T; status: string } {
  return v.status !== 'unknown' && v.value !== null
}
function cefrText(c: CourseSummary): string | null {
  const lc = c.language_course
  if (!known(lc.cefr_entry) && !known(lc.cefr_exit)) return null
  const entry = known(lc.cefr_entry) ? lc.cefr_entry.value : '?'
  const exit = known(lc.cefr_exit) ? lc.cefr_exit.value : '?'
  return t('courses.values.cefr', { entry, exit })
}
const ilepNote = (c: CourseSummary) => c.intl_authorization.notes.find((n) => n.code === 'ie.ilep_end')
</script>

<template>
  <section aria-labelledby="courses-title">
    <p class="eyebrow">{{ t('courses.eyebrow') }}</p>
    <h1 id="courses-title">{{ t('courses.title') }}</h1>
    <p class="intro">{{ t('courses.intro') }}</p>
    <p class="stay">{{ t('courses.stay') }}</p>
  </section>

  <button
    type="button"
    class="filters-toggle button-quiet"
    :aria-expanded="filtersOpen"
    aria-controls="course-filters"
    @click="filtersOpen = !filtersOpen"
  >
    {{ t('courses.filters.toggle', { n: num(activeCount) }) }}
    <span aria-hidden="true">{{ filtersOpen ? '▴' : '▾' }}</span>
  </button>

  <form id="course-filters" :class="['filters', 'card', { open: filtersOpen }]" :aria-label="t('courses.filters.heading')" @submit.prevent>
    <div class="mine" data-test="mine">
      <label class="check">
        <input
          type="checkbox"
          :checked="filters.mine && !!myBand"
          :disabled="!myBand"
          data-test="mine-toggle"
          @change="change({ mine: ($event.target as HTMLInputElement).checked, level: undefined })"
        />
        {{ t('courses.filters.mine') }}
      </label>
      <p v-if="myBand" class="hint">{{ t('courses.filters.mineHint', { level: myBand }) }}</p>
      <p v-else class="hint">
        {{ t('courses.filters.mineNone') }}
        <RouterLink :to="`/${prefix}/placement`">{{ t('courses.filters.mineTest') }}</RouterLink>
      </p>
    </div>

    <div class="field">
      <label for="course-city">{{ t('courses.filters.city') }}</label>
      <select id="course-city" :value="filters.city ?? ''" data-test="city-select" @change="change({ city: selectValue($event) })">
        <option value="">{{ t('courses.filters.anyCity') }}</option>
        <option v-if="filters.city && !facets?.cities.some((c) => c.city === filters.city)" :value="filters.city">{{ filters.city }}</option>
        <option v-for="c in facets?.cities ?? []" :key="c.city" :value="c.city">{{ withCount(c.city, c.count) }}</option>
      </select>
    </div>

    <div class="field">
      <label for="course-exam">{{ t('courses.filters.exam') }}</label>
      <select id="course-exam" :value="filters.exam ?? ''" data-test="exam-select" @change="change({ exam: selectValue($event) as CourseFilters['exam'] })">
        <option value="">{{ t('courses.filters.anyExam') }}</option>
        <option v-for="e in EXAMS" :key="e" :value="e">{{ withCount(examName(e), facets?.exam[e]) }}</option>
      </select>
    </div>

    <div class="field">
      <label for="course-level">{{ t('courses.filters.level') }}</label>
      <select
        id="course-level"
        :value="level ?? ''"
        :disabled="filters.mine && !!myBand"
        data-test="level-select"
        @change="change({ level: selectValue($event) as CourseFilters['level'] })"
      >
        <option value="">{{ t('courses.filters.anyLevel') }}</option>
        <option v-for="b in CEFR_BANDS" :key="b" :value="b">{{ t('courses.filters.levelOption', { band: b }) }}</option>
      </select>
      <p v-if="level && facets?.cefr_entry.unknown" class="hint">
        {{ t('courses.filters.levelUnknown', { n: num(facets.cefr_entry.unknown) }, facets.cefr_entry.unknown) }}
      </p>
    </div>

    <div class="field">
      <label for="course-hours">{{ t('courses.filters.hours') }}</label>
      <select
        id="course-hours"
        :value="filters.hoursMin ?? ''"
        data-test="hours-select"
        @change="change({ hoursMin: selectValue($event) ? Number(selectValue($event)) : undefined })"
      >
        <option value="">{{ t('courses.filters.anyHours') }}</option>
        <option v-for="h in HOURS_OPTIONS" :key="h" :value="h">{{ t('courses.filters.hoursOption', { n: h }) }}</option>
      </select>
    </div>

    <button v-if="activeCount > 0" type="button" class="button-quiet clear" @click="clearFilters">{{ t('courses.filters.clear') }}</button>
  </form>

  <StatusLegend class="legend-block" />

  <div class="results" :aria-busy="load.state === 'loading'">
    <p class="count" aria-live="polite">
      <template v-if="load.state === 'ok'">{{ t('courses.count', { n: num(load.data.total) }, load.data.total) }}</template>
    </p>

    <p v-if="load.state === 'loading'" class="state-message">{{ t('courses.loading') }}</p>

    <div v-else-if="load.state === 'error'" class="state-message card" role="alert">
      <p>{{ t('courses.error') }}</p>
      <button type="button" class="button-quiet" @click="fetchCourses">{{ t('programs.retry') }}</button>
    </div>

    <template v-else>
      <div v-if="load.data.items.length === 0" class="state-message card">
        <p>{{ t('courses.empty') }}</p>
        <button v-if="activeCount > 0" type="button" class="button-quiet" @click="clearFilters">{{ t('courses.filters.clear') }}</button>
      </div>

      <ul v-else class="course-list">
        <li v-for="c in load.data.items" :key="c.id" class="course card" data-test="course-row">
          <h2 class="course-title">
            <RouterLink :to="`/${prefix}/english-courses/${c.id}`">{{ c.title }}</RouterLink>
          </h2>
          <p class="where">
            {{ c.institution.name }} ·
            <template v-if="c.campus.city">{{ c.campus.city }}</template>
            <span v-else class="muted" data-test="city-unknown">{{ t('courses.values.cityUnknown') }}</span>
          </p>

          <dl class="facts">
            <div>
              <dt>{{ t('courses.fields.exam') }}</dt>
              <dd v-if="known(c.language_course.exam)">{{ examName(c.language_course.exam.value) }}</dd>
              <dd v-else><span class="muted">{{ t('courses.values.unknown') }}</span> <StatusBadge status="unknown" /></dd>
            </div>
            <div>
              <dt>{{ t('courses.fields.cefr') }}</dt>
              <dd v-if="cefrText(c)" data-test="cefr">{{ cefrText(c) }}</dd>
              <dd v-else><span class="muted">{{ t('courses.values.unknown') }}</span> <StatusBadge status="unknown" /></dd>
            </div>
            <div>
              <dt>{{ t('courses.fields.weeks') }}</dt>
              <dd v-if="known(c.language_course.weeks)">{{ t('courses.values.weeks', { n: num(c.language_course.weeks.value) }) }}</dd>
              <dd v-else><span class="muted">{{ t('courses.values.unknown') }}</span> <StatusBadge status="unknown" /></dd>
            </div>
            <div>
              <dt>{{ t('courses.fields.hours') }}</dt>
              <dd v-if="known(c.language_course.hours_per_week)">{{ t('courses.values.hours', { n: num(c.language_course.hours_per_week.value) }) }}</dd>
              <dd v-else><span class="muted">{{ t('courses.values.unknown') }}</span> <StatusBadge status="unknown" /></dd>
            </div>
            <div data-test="price">
              <dt>{{ t('courses.fields.price') }}</dt>
              <dd v-if="known(c.language_course.price)">
                {{ formatMoney(c.language_course.price.value, locale) }} <StatusBadge :status="c.language_course.price.status" />
              </dd>
              <dd v-else><span class="muted">{{ t('courses.values.unknown') }}</span> <StatusBadge status="unknown" /></dd>
            </div>
            <div data-test="start-dates">
              <dt>{{ t('courses.fields.startDates') }}</dt>
              <dd v-if="c.language_course.start_dates.length">{{ c.language_course.start_dates.map((d) => d.value).join(', ') }}</dd>
              <dd v-else><span class="muted">{{ t('courses.values.unknown') }}</span> <StatusBadge status="unknown" /></dd>
            </div>
          </dl>

          <div class="lists" data-test="authorization">
            <span class="lists-label">{{ t('courses.fields.authorization') }}</span>
            <template v-if="c.intl_authorization.value && c.intl_authorization.status !== 'unknown'">
              <span class="list-name">{{ listName(c.intl_authorization.value.scheme) }}</span>
              <StatusBadge :status="c.intl_authorization.status" />
            </template>
            <template v-else>
              <span class="muted">{{ t('courses.values.notFound') }}</span>
              <StatusBadge status="unknown" />
            </template>
          </div>
          <p v-if="ilepNote(c)" class="notice" data-test="ilep-notice">{{ t('courses.notes.ie_ilep_end') }}</p>
        </li>
      </ul>

      <nav v-if="pages > 1" class="pagination" :aria-label="t('programs.pagination.label')">
        <RouterLink v-if="filters.page > 1" :to="pageLink(filters.page - 1)" rel="prev">{{ t('programs.pagination.prev') }}</RouterLink>
        <span v-else class="muted" aria-hidden="true">{{ t('programs.pagination.prev') }}</span>
        <span aria-current="page">{{ t('programs.pagination.page', { page: num(filters.page), pages: num(pages) }) }}</span>
        <RouterLink v-if="filters.page < pages" :to="pageLink(filters.page + 1)" rel="next">{{ t('programs.pagination.next') }}</RouterLink>
        <span v-else class="muted" aria-hidden="true">{{ t('programs.pagination.next') }}</span>
      </nav>
    </template>
  </div>
</template>

<style scoped>
h1 {
  margin-block: 0.25rem 0.5rem;
  font-size: clamp(1.75rem, 5vw, 2.25rem);
}
.intro {
  margin-block: 0 0.5rem;
  color: var(--text-muted);
}
.stay {
  margin-block: 0 1.5rem;
  font-size: 0.875rem;
  color: var(--text-muted);
  max-inline-size: var(--measure);
}
.filters {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 1rem 1.25rem;
  align-items: start;
  margin-block-end: 1rem;
}
.mine {
  grid-column: 1 / -1;
}
.check {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-inline-size: 0;
}
.field label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}
select {
  font: inherit;
  font-size: 0.875rem;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--field-border);
  border-radius: var(--radius);
  padding-block: 0.3125rem;
  padding-inline: 0.5rem;
  max-inline-size: 100%;
}
select:hover:not(:disabled) {
  border-color: var(--accent);
}
.hint {
  margin-block: 0.25rem 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.clear {
  align-self: end;
  justify-self: start;
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
.button-quiet:hover {
  border-color: var(--accent-dim);
}
.filters-toggle {
  display: none;
}
.legend-block {
  margin-block-end: 1.5rem;
}
.count {
  margin-block: 0 0.75rem;
  font-family: var(--font-mono);
  font-size: 0.875rem;
}
.state-message {
  color: var(--text-muted);
}
.state-message p {
  margin-block: 0 0.75rem;
}
.course-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}
.course-title {
  margin: 0;
  font-size: 1.0625rem;
}
.course-title a {
  color: var(--text);
  text-decoration-color: var(--accent-dim);
}
.course-title a:hover {
  color: var(--accent-text);
}
.where {
  margin-block: 0.125rem 0.75rem;
  color: var(--text-muted);
  font-size: 0.9375rem;
}
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: 0.5rem 1.25rem;
  margin: 0;
}
.facts dt {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.facts dd {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
  font-size: 0.875rem;
}
.lists {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
  margin-block-start: 0.75rem;
  font-size: 0.875rem;
}
.lists-label {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.list-name {
  font-weight: 600;
}
.notice {
  margin-block: 0.5rem 0;
  padding-inline-start: 0.75rem;
  border-inline-start: 2px solid var(--accent-dim);
  font-size: 0.875rem;
  max-inline-size: none;
}
.muted {
  color: var(--text-muted);
}
.pagination {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem 1rem;
  margin-block-start: 1.5rem;
  font-family: var(--font-mono);
  font-size: 0.875rem;
}
@media (max-width: 40rem) {
  .filters-toggle {
    display: inline-flex;
    gap: 0.5rem;
    margin-block-end: 0.75rem;
  }
  .filters:not(.open) {
    display: none;
  }
}
</style>
