<script setup lang="ts">
// Filter panel of the program list (FR-16, contract v0.2 §2). Counts come from GET /api/facets
// (whole state, other filters ignored); without facets the filters still work, just uncounted.
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ACCREDITED_FILTERS,
  CIP_FAMILIES,
  type CipFamily,
  type Facets,
  GRADUATES_FILTERS,
  INSTITUTION_CONTROLS,
  type InstitutionControl,
  SEVP_FILTERS,
  STEM_FILTERS,
} from '../api/types'
import { formatMoney, formatNumber } from '../format'
import type { ProgramFilters } from '../programFilters'
import { CIP_FAMILY_KEYS } from '../programs'

const props = defineProps<{
  filters: ProgramFilters
  facets: Facets | null
  /** IPEDS year of the completions shown, e.g. "2023-24", when known. */
  graduatesYear?: string
  /** Active filter groups; "Clear filters" shows only when there is something to clear. */
  activeCount: number
}>()
const emit = defineEmits<{ change: [changes: Partial<ProgramFilters>]; clear: [] }>()
const { t, locale } = useI18n()

const num = (n: number) => formatNumber(n, locale.value)
function count(n: number | undefined): string {
  return n === undefined ? '' : num(n)
}

// Search: typed text goes to the URL after a short pause, or at once on Enter.
const searchText = ref(props.filters.q)
watch(
  () => props.filters.q,
  (value) => {
    if (value !== searchText.value.trim()) searchText.value = value
  },
)
let searchTimer: ReturnType<typeof setTimeout> | undefined
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(submitSearch, 350)
}
function submitSearch() {
  clearTimeout(searchTimer)
  const value = searchText.value.trim()
  if (value !== props.filters.q) emit('change', { q: value })
}
onBeforeUnmount(() => clearTimeout(searchTimer))

function toggle<T extends string>(list: readonly T[], all: readonly T[], value: T, checked: boolean): T[] {
  const next = checked ? [...list, value] : list.filter((v) => v !== value)
  return all.filter((v) => next.includes(v))
}
function toggleFamily(family: CipFamily, checked: boolean) {
  emit('change', { cip: toggle(props.filters.cip, CIP_FAMILIES, family, checked) })
}
function toggleControl(control: InstitutionControl, checked: boolean) {
  emit('change', { control: toggle(props.filters.control, INSTITUTION_CONTROLS, control, checked) })
}

// Cities: a searchable checkbox list; selected cities stay on top.
const cityQuery = ref('')
const cityOptions = computed(() => {
  const known = props.facets?.cities ?? []
  const selected = props.filters.city.map((city) => known.find((c) => c.city === city) ?? { city, count: undefined })
  const needle = cityQuery.value.trim().toLocaleLowerCase(locale.value)
  const rest = known.filter((c) => !props.filters.city.includes(c.city) && (!needle || c.city.toLocaleLowerCase(locale.value).includes(needle)))
  return [...selected, ...rest]
})
function toggleCity(city: string, checked: boolean) {
  const next = checked ? [...props.filters.city, city] : props.filters.city.filter((c) => c !== city)
  emit('change', { city: next })
}

// Tuition range: applied on change (blur or Enter), not on every keystroke.
const minText = ref<string | number>(props.filters.minTuition?.toString() ?? '')
const maxText = ref<string | number>(props.filters.maxTuition?.toString() ?? '')
watch(
  () => [props.filters.minTuition, props.filters.maxTuition],
  ([min, max]) => {
    minText.value = min?.toString() ?? ''
    maxText.value = max?.toString() ?? ''
  },
)
// v-model on a number input hands back a number, or "" when the field is empty.
function parseAmount(raw: string | number): number | undefined | null {
  const text = String(raw).trim()
  if (text === '') return undefined
  const n = Number(text)
  return Number.isFinite(n) && n >= 0 ? n : null
}
const rangeError = computed(() => {
  const min = parseAmount(minText.value)
  const max = parseAmount(maxText.value)
  if (min === null || max === null) return t('programs.filters.tuitionInvalid')
  if (min !== undefined && max !== undefined && max < min) return t('programs.filters.tuitionOrder')
  return ''
})
function applyRange() {
  if (rangeError.value) return
  const minTuition = parseAmount(minText.value) ?? undefined
  const maxTuition = parseAmount(maxText.value) ?? undefined
  if (minTuition !== props.filters.minTuition || maxTuition !== props.filters.maxTuition) emit('change', { minTuition, maxTuition })
}
const tuitionFacet = computed(() => props.facets?.tuition ?? null)
function moneyHint(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return ''
  return formatMoney({ amount, currency: tuitionFacet.value?.currency ?? 'USD' }, locale.value)
}

const graduatesLegend = computed(() =>
  props.graduatesYear ? t('programs.filters.graduatesIn', { year: props.graduatesYear }) : t('programs.filters.graduates'),
)
</script>

<template>
  <form class="filters" role="search" :aria-label="t('programs.filters.heading')" @submit.prevent="submitSearch(); applyRange()">
    <div class="filter search">
      <label for="program-search" class="filter-label">{{ t('programs.filters.search') }}</label>
      <input
        id="program-search"
        v-model="searchText"
        type="search"
        :placeholder="t('programs.filters.searchPlaceholder')"
        autocomplete="off"
        @input="onSearchInput"
      />
    </div>

    <fieldset class="filter">
      <legend class="filter-label">{{ t('programs.filters.cipFamily') }}</legend>
      <label v-for="family in CIP_FAMILIES" :key="family" class="option">
        <input type="checkbox" :checked="filters.cip.includes(family)" @change="toggleFamily(family, ($event.target as HTMLInputElement).checked)" />
        <span class="option-text"><code>{{ family }}</code> {{ t(`programs.cipFamilies.${CIP_FAMILY_KEYS[family]}`) }}</span>
        <span class="n" data-test="facet-count">{{ count(facets?.cip_family[family]) }}</span>
      </label>
    </fieldset>

    <fieldset class="filter" data-test="filter-control">
      <legend class="filter-label">{{ t('programs.filters.control') }}</legend>
      <label v-for="control in INSTITUTION_CONTROLS" :key="control" class="option">
        <input type="checkbox" :checked="filters.control.includes(control)" @change="toggleControl(control, ($event.target as HTMLInputElement).checked)" />
        <span class="option-text">{{ t(`programs.controlFilter.${control}`) }}</span>
        <span class="n" data-test="facet-count">{{ count(facets?.control[control]) }}</span>
      </label>
    </fieldset>

    <fieldset class="filter">
      <legend class="filter-label">{{ t('programs.filters.stem') }}</legend>
      <label class="option">
        <input type="radio" name="stem" value="" :checked="!filters.stem" @change="emit('change', { stem: undefined })" />
        <span class="option-text">{{ t('programs.filters.any') }}</span>
      </label>
      <label v-for="value in STEM_FILTERS" :key="value" class="option">
        <input type="radio" name="stem" :value="value" :checked="filters.stem === value" @change="emit('change', { stem: value })" />
        <span class="option-text">{{ t(`programs.stemFilter.${value}`) }}</span>
        <span class="n" data-test="facet-count">{{ count(facets?.stem[value]) }}</span>
      </label>
    </fieldset>

    <fieldset class="filter">
      <legend class="filter-label">{{ t('programs.filters.sevp') }}</legend>
      <label class="option">
        <input type="radio" name="sevp" value="" :checked="!filters.sevp" @change="emit('change', { sevp: undefined })" />
        <span class="option-text">{{ t('programs.filters.any') }}</span>
      </label>
      <label v-for="value in SEVP_FILTERS" :key="value" class="option">
        <input type="radio" name="sevp" :value="value" :checked="filters.sevp === value" @change="emit('change', { sevp: value })" />
        <span class="option-text">{{ t(`programs.checkFilter.${value === 'confirmed' ? 'confirmed' : 'unknown'}`) }}</span>
        <span class="n" data-test="facet-count">{{ count(facets?.sevp[value]) }}</span>
      </label>
    </fieldset>

    <fieldset class="filter">
      <legend class="filter-label">{{ t('programs.filters.accreditation') }}</legend>
      <label class="option">
        <input type="radio" name="accredited" value="" :checked="!filters.accredited" @change="emit('change', { accredited: undefined })" />
        <span class="option-text">{{ t('programs.filters.any') }}</span>
      </label>
      <label v-for="value in ACCREDITED_FILTERS" :key="value" class="option">
        <input type="radio" name="accredited" :value="value" :checked="filters.accredited === value" @change="emit('change', { accredited: value })" />
        <span class="option-text">{{ t(`programs.checkFilter.${value === 'true' ? 'confirmed' : 'unknown'}`) }}</span>
        <span class="n" data-test="facet-count">{{ count(facets?.accredited[value]) }}</span>
      </label>
    </fieldset>

    <fieldset class="filter">
      <legend class="filter-label">{{ graduatesLegend }}</legend>
      <label class="option">
        <input type="radio" name="has_graduates" value="" :checked="!filters.hasGraduates" @change="emit('change', { hasGraduates: undefined })" />
        <span class="option-text">{{ t('programs.filters.any') }}</span>
      </label>
      <label v-for="value in GRADUATES_FILTERS" :key="value" class="option">
        <input type="radio" name="has_graduates" :value="value" :checked="filters.hasGraduates === value" @change="emit('change', { hasGraduates: value })" />
        <span class="option-text">{{ t(`programs.graduatesFilter.${value}`) }}</span>
        <span class="n" data-test="facet-count">{{ count(facets?.has_graduates[value]) }}</span>
      </label>
    </fieldset>

    <fieldset class="filter">
      <legend class="filter-label">{{ t('programs.filters.tuition') }}</legend>
      <div class="range">
        <label class="range-field">
          <span class="range-label">{{ t('programs.filters.tuitionMin') }}</span>
          <input
            v-model="minText"
            type="number"
            inputmode="numeric"
            min="0"
            step="100"
            data-test="tuition-min"
            :placeholder="moneyHint(tuitionFacet?.min)"
            :aria-invalid="!!rangeError"
            :aria-describedby="rangeError ? 'tuition-error' : 'tuition-hint'"
            @change="applyRange"
          />
        </label>
        <label class="range-field">
          <span class="range-label">{{ t('programs.filters.tuitionMax') }}</span>
          <input
            v-model="maxText"
            type="number"
            inputmode="numeric"
            min="0"
            step="100"
            data-test="tuition-max"
            :placeholder="moneyHint(tuitionFacet?.max)"
            :aria-invalid="!!rangeError"
            :aria-describedby="rangeError ? 'tuition-error' : 'tuition-hint'"
            @change="applyRange"
          />
        </label>
      </div>
      <p v-if="rangeError" id="tuition-error" class="hint error" role="alert">{{ rangeError }}</p>
      <p v-else id="tuition-hint" class="hint">
        {{ t('programs.filters.tuitionHint') }}
        <template v-if="tuitionFacet && tuitionFacet.unknown > 0">
          {{ t('programs.filters.tuitionUnknown', { n: num(tuitionFacet.unknown) }, tuitionFacet.unknown) }}
        </template>
      </p>
    </fieldset>

    <fieldset class="filter cities">
      <legend class="filter-label">{{ t('programs.filters.city') }}</legend>
      <label for="city-search" class="visually-hidden">{{ t('programs.filters.citySearch') }}</label>
      <input id="city-search" v-model="cityQuery" type="search" class="city-search" autocomplete="off" :placeholder="t('programs.filters.citySearch')" />
      <div class="city-list" role="group" :aria-label="t('programs.filters.city')">
        <label v-for="c in cityOptions" :key="c.city" class="option">
          <input type="checkbox" :checked="filters.city.includes(c.city)" @change="toggleCity(c.city, ($event.target as HTMLInputElement).checked)" />
          <span class="option-text">{{ c.city }}</span>
          <span class="n" data-test="facet-count">{{ count(c.count) }}</span>
        </label>
        <p v-if="cityOptions.length === 0" class="hint">{{ t('programs.filters.cityNone') }}</p>
      </div>
    </fieldset>

    <div v-if="activeCount > 0" class="filter-actions">
      <button type="button" class="button-quiet" data-test="clear-filters" @click="emit('clear')">
        {{ t('programs.filters.clear') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 1rem 1.5rem;
}
.filter {
  margin: 0;
  padding: 0;
  border: 0;
  min-inline-size: 0;
}
.search {
  grid-column: 1 / -1;
}
.filter-label {
  display: block;
  margin-block-end: 0.375rem;
  padding: 0;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}
input[type='search'],
input[type='number'] {
  inline-size: 100%;
  font: inherit;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding-block: 0.4375rem;
  padding-inline: 0.75rem;
}
input[type='search']:hover,
input[type='number']:hover {
  border-color: var(--accent-dim);
}
input[aria-invalid='true'] {
  border-color: var(--text);
}
input::placeholder {
  color: var(--text-muted);
  opacity: 1;
}
.option {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  padding-block: 0.125rem;
  font-size: 0.9375rem;
  cursor: pointer;
}
.option-text {
  flex: 1;
  min-inline-size: 0;
}
.option code {
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.n {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}
input[type='checkbox'],
input[type='radio'] {
  accent-color: var(--accent);
}
.range {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.range-label {
  display: block;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.hint {
  margin-block: 0.375rem 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.hint.error {
  color: var(--text);
  font-weight: 600;
}
.city-search {
  margin-block-end: 0.375rem;
}
.city-list {
  max-block-size: 11rem;
  overflow-y: auto;
  padding-inline-end: 0.25rem;
  border-block: 1px solid var(--border);
  padding-block: 0.25rem;
}
.filter-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
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
</style>
