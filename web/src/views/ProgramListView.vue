<script setup lang="ts">
// FR-16: program list with filters and sort reflected in the URL query (NFR-15: shareable links).
// Contract v0.2: price in each row, more filters with counts from /api/facets, sorting.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { getFacets, listPrograms } from '../api/client'
import { type Facets, type ProgramList, SORT_KEYS, type SortKey } from '../api/types'
import CompletionsText from '../components/CompletionsText.vue'
import ProgramFilters from '../components/ProgramFilters.vue'
import ProgramTable from '../components/ProgramTable.vue'
import StatusBadge from '../components/StatusBadge.vue'
import StatusLegend from '../components/StatusLegend.vue'
import TuitionPrice from '../components/TuitionPrice.vue'
import { formatNumber, placeLabel } from '../format'
import {
  activeFilterCount,
  clearedFilters,
  DEFAULT_ORDER,
  parseFilters,
  type ProgramFilters as Filters,
  toApiQuery,
  toUrlQuery,
} from '../programFilters'
import { stemKey, useLocalePrefix } from '../programs'

const PAGE_SIZE = 25

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const prefix = useLocalePrefix()

// The URL is the single source of truth for filters, sort, page and view.
const filters = computed(() => parseFilters(route.query))
const view = computed<'cards' | 'table'>(() => (route.query.view === 'table' ? 'table' : 'cards'))
const activeCount = computed(() => activeFilterCount(filters.value))

type Load = { state: 'loading' } | { state: 'error' } | { state: 'ok'; data: ProgramList }
const load = ref<Load>({ state: 'loading' })
let controller: AbortController | undefined

async function fetchPrograms() {
  controller?.abort()
  controller = new AbortController()
  const signal = controller.signal
  load.value = { state: 'loading' }
  try {
    const data = await listPrograms(toApiQuery(filters.value, PAGE_SIZE), signal)
    if (!signal.aborted) load.value = { state: 'ok', data }
  } catch (error) {
    if (!signal.aborted) load.value = { state: 'error' }
    if ((error as Error)?.name !== 'AbortError') console.warn('programs: load failed', error)
  }
}

watch(() => JSON.stringify(toApiQuery(filters.value, PAGE_SIZE)), fetchPrograms, { immediate: true })
onBeforeUnmount(() => controller?.abort())

// Facets (counts next to filter options) for the current state; the list works without them.
const facets = ref<Facets | null>(null)
let facetsController: AbortController | undefined
async function fetchFacets() {
  facetsController?.abort()
  facetsController = new AbortController()
  const signal = facetsController.signal
  try {
    const data = await getFacets(filters.value.state, signal)
    if (!signal.aborted) facets.value = data
  } catch (error) {
    if (!signal.aborted) facets.value = null
    if ((error as Error)?.name !== 'AbortError') console.warn('facets: load failed', error)
  }
}
watch(() => filters.value.state, fetchFacets, { immediate: true })
onBeforeUnmount(() => facetsController?.abort())

// IPEDS year of the completions, for the "Graduates in <year>" filter label.
const graduatesYear = ref<string | undefined>()
watch(load, (value) => {
  if (value.state !== 'ok') return
  const year = value.data.items.find((i) => i.completions.value)?.completions.value?.year
  if (year) graduatesYear.value = year
})

function navigate(next: Filters) {
  const extra = view.value === 'table' ? { view: 'table' } : {}
  router.replace({ query: toUrlQuery(next, extra) })
}
function onChange(changes: Partial<Filters>) {
  navigate({ ...filters.value, ...changes, page: 1 }) // any filter change goes back to page 1
}
function clearFilters() {
  navigate(clearedFilters(filters.value))
}

// Sorting: picking a field starts in its natural order (cheapest first, most graduates first).
function setSort(key: SortKey) {
  navigate({ ...filters.value, sort: key, order: DEFAULT_ORDER[key], page: 1 })
}
function toggleOrder() {
  navigate({ ...filters.value, order: filters.value.order === 'asc' ? 'desc' : 'asc', page: 1 })
}
function sortFromHeader(key: SortKey) {
  if (key === filters.value.sort) toggleOrder()
  else setSort(key)
}
const orderWord = computed(() => t(`programs.sort.${filters.value.order}`))
const otherOrderWord = computed(() => t(`programs.sort.${filters.value.order === 'asc' ? 'desc' : 'asc'}`))

function setView(next: 'cards' | 'table') {
  const query = { ...route.query, view: next === 'table' ? 'table' : undefined }
  router.replace({ query })
}

// Narrow screens: the panel collapses behind a "Filters (n)" button.
const filtersOpen = ref(false)

const pages = computed(() => (load.value.state === 'ok' ? Math.max(1, Math.ceil(load.value.data.total / PAGE_SIZE)) : 1))
function pageLink(n: number) {
  return { query: { ...route.query, page: n > 1 ? String(n) : undefined } }
}
const page = computed(() => filters.value.page)

const num = (n: number) => formatNumber(n, locale.value)
</script>

<template>
  <section aria-labelledby="programs-title">
    <p class="eyebrow">{{ t('programs.eyebrow') }}</p>
    <h1 id="programs-title">{{ t('programs.title') }}</h1>
    <p class="intro">{{ t('programs.intro') }}</p>
  </section>

  <button
    type="button"
    class="filters-toggle button-quiet"
    data-test="filters-toggle"
    :aria-expanded="filtersOpen"
    aria-controls="program-filters"
    @click="filtersOpen = !filtersOpen"
  >
    {{ t('programs.filters.toggle', { n: num(activeCount) }) }}
    <span aria-hidden="true">{{ filtersOpen ? '▴' : '▾' }}</span>
  </button>

  <div id="program-filters" :class="['filters-panel', 'card', { open: filtersOpen }]">
    <ProgramFilters
      :filters="filters"
      :facets="facets"
      :graduates-year="graduatesYear"
      :active-count="activeCount"
      @change="onChange"
      @clear="clearFilters"
    />
  </div>

  <StatusLegend class="legend-block" />

  <div class="results" :aria-busy="load.state === 'loading'">
    <div class="results-bar">
      <p class="count" aria-live="polite">
        <template v-if="load.state === 'ok'">{{ t('programs.count', { n: num(load.data.total) }, load.data.total) }}</template>
      </p>
      <div class="sort-controls">
        <label for="program-sort" class="sort-label">{{ t('programs.sort.label') }}</label>
        <select id="program-sort" :value="filters.sort" data-test="sort-select" @change="setSort(($event.target as HTMLSelectElement).value as SortKey)">
          <option v-for="key in SORT_KEYS" :key="key" :value="key">{{ t(`programs.sort.keys.${key}`) }}</option>
        </select>
        <button
          type="button"
          class="button-quiet order-toggle"
          data-test="order-toggle"
          :aria-label="t('programs.sort.orderAria', { order: orderWord, other: otherOrderWord })"
          @click="toggleOrder"
        >
          <span aria-hidden="true">{{ filters.order === 'asc' ? '↑' : '↓' }}</span> {{ orderWord }}
        </button>
        <div class="view-toggle" role="group" :aria-label="t('programs.view.label')">
          <button type="button" class="button-quiet" :aria-pressed="view === 'cards'" data-test="view-cards" @click="setView('cards')">
            {{ t('programs.view.cards') }}
          </button>
          <button type="button" class="button-quiet" :aria-pressed="view === 'table'" data-test="view-table" @click="setView('table')">
            {{ t('programs.view.table') }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="load.state === 'loading'" class="state-message">{{ t('programs.loading') }}</p>

    <div v-else-if="load.state === 'error'" class="state-message card" role="alert">
      <p>{{ t('programs.error') }}</p>
      <button type="button" class="button-quiet" @click="fetchPrograms">{{ t('programs.retry') }}</button>
    </div>

    <template v-else>
      <div v-if="load.data.items.length === 0" class="state-message card">
        <p>{{ t('programs.empty') }}</p>
        <button v-if="activeCount > 0" type="button" class="button-quiet" @click="clearFilters">
          {{ t('programs.filters.clear') }}
        </button>
      </div>

      <template v-else>
        <ProgramTable
          v-if="view === 'table'"
          class="table-view"
          :items="load.data.items"
          :sort="filters.sort"
          :order="filters.order"
          @sort="sortFromHeader"
        />

        <ul :class="['program-list', { 'cards-narrow-only': view === 'table' }]">
          <li v-for="item in load.data.items" :key="item.id" class="program card" data-test="program-row">
            <div class="program-head">
              <h2 class="program-title">
                <RouterLink :to="`/${prefix}/programs/${item.id}`">{{ item.title }}</RouterLink>
              </h2>
              <p class="program-where">
                {{ item.institution.name }} · {{ placeLabel(item.campus.city, item.campus.state) }}
              </p>
            </div>

            <dl class="facts">
              <div class="wide price-fact">
                <dt>{{ t('program.tuition') }}</dt>
                <dd><TuitionPrice :tuition="item.graduate_tuition_nonresident" /></dd>
              </div>
              <div>
                <dt>{{ t('program.cip') }}</dt>
                <dd><code>{{ item.cip.code }}</code></dd>
              </div>
              <div>
                <dt>{{ t('program.stem') }}</dt>
                <dd>
                  <span>{{ t(stemKey(item.stem_opt)) }}</span>
                  <StatusBadge :status="item.stem_opt.status" />
                </dd>
              </div>
              <div>
                <dt>{{ t('program.sevp') }}</dt>
                <dd><StatusBadge :status="item.sevp_status" /></dd>
              </div>
              <div>
                <dt>{{ t('program.accreditation') }}</dt>
                <dd><StatusBadge :status="item.accreditation_status" /></dd>
              </div>
              <div class="wide">
                <dt>{{ t('program.completions') }}</dt>
                <dd>
                  <CompletionsText :completions="item.completions" />
                  <StatusBadge :status="item.completions.status" />
                </dd>
              </div>
            </dl>

            <p v-if="item.flags.includes('no_stem_opt_extension')" class="flag">
              <strong>{{ t('program.flags.no_stem_opt_extension.title') }}</strong>
              {{ t('program.flags.no_stem_opt_extension.body') }}
            </p>
          </li>
        </ul>
      </template>

      <nav v-if="pages > 1" class="pagination" :aria-label="t('programs.pagination.label')">
        <RouterLink v-if="page > 1" :to="pageLink(page - 1)" rel="prev">{{ t('programs.pagination.prev') }}</RouterLink>
        <span v-else class="muted" aria-hidden="true">{{ t('programs.pagination.prev') }}</span>
        <span aria-current="page">{{ t('programs.pagination.page', { page: num(page), pages: num(pages) }) }}</span>
        <RouterLink v-if="page < pages" :to="pageLink(page + 1)" rel="next">{{ t('programs.pagination.next') }}</RouterLink>
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
  margin-block: 0 1.5rem;
  color: var(--text-muted);
}
.filters-panel {
  margin-block-end: 1rem;
}
.filters-toggle {
  display: none;
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
.button-quiet[aria-pressed='true'] {
  border-color: var(--accent);
}
.legend-block {
  margin-block-end: 1.5rem;
}
.results-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  margin-block-end: 0.75rem;
}
.count {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 0.875rem;
}
.sort-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.sort-label {
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
select:hover {
  border-color: var(--accent);
}
.order-toggle {
  white-space: nowrap;
}
.view-toggle {
  display: inline-flex;
  gap: 0.25rem;
  margin-inline-start: 0.5rem;
}
.state-message {
  color: var(--text-muted);
}
.state-message p {
  margin-block: 0 0.75rem;
}
.program-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}
.program-title {
  margin: 0;
  font-size: 1.0625rem;
}
.program-title a {
  color: var(--text);
  text-decoration-color: var(--accent-dim);
}
.program-title a:hover {
  color: var(--accent-text);
}
.program-where {
  margin-block: 0.125rem 0.75rem;
  color: var(--text-muted);
  font-size: 0.9375rem;
}
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr));
  gap: 0.5rem 1.25rem;
  margin: 0;
}
.facts .wide {
  grid-column: span 2;
}
.facts .price-fact {
  grid-column: 1 / -1;
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
.price-fact dd {
  font-size: 0.9375rem;
}
.muted {
  color: var(--text-muted);
}
.flag {
  margin-block: 0.75rem 0;
  padding-inline-start: 0.75rem;
  border-inline-start: 2px solid var(--text-muted);
  font-size: 0.875rem;
  max-inline-size: none;
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
/* Wide screens may use the table; narrow ones always get cards. */
@media (min-width: 48rem) {
  .cards-narrow-only {
    display: none;
  }
}
@media (max-width: 47.99rem) {
  .table-view,
  .view-toggle {
    display: none;
  }
}
@media (max-width: 40rem) {
  .filters-toggle {
    display: inline-flex;
    gap: 0.5rem;
    margin-block-end: 0.75rem;
  }
  .filters-panel:not(.open) {
    display: none;
  }
}
@media (max-width: 30rem) {
  .facts .wide {
    grid-column: auto;
  }
}
</style>
