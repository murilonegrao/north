<script setup lang="ts">
// Compact comparison table for wide screens. Column headers sort the list (aria-sort on the
// sorted column); the same sort lives in the URL as with the "Sort by" select. City sits under the
// institution to keep the table inside the page width; sorting by city stays in the select.
import { useI18n } from 'vue-i18n'
import type { ProgramSummary, SortKey, SortOrder } from '../api/types'
import { formatNumber } from '../format'
import { stemKey, useLocalePrefix } from '../programs'
import StatusBadge from './StatusBadge.vue'
import TuitionPrice from './TuitionPrice.vue'

const props = defineProps<{ items: ProgramSummary[]; sort: SortKey; order: SortOrder }>()
const emit = defineEmits<{ sort: [key: SortKey] }>()
const { t, locale } = useI18n()
const prefix = useLocalePrefix()

const COLUMNS: Array<{ key: SortKey; label: string; numeric?: boolean }> = [
  { key: 'title', label: 'programs.sort.keys.title' },
  { key: 'institution', label: 'programs.sort.keys.institution' },
  { key: 'tuition', label: 'programs.table.tuition', numeric: true },
  { key: 'graduates', label: 'programs.table.graduates', numeric: true },
  { key: 'nonresident_share', label: 'programs.table.share', numeric: true },
]

function ariaSort(key: SortKey): 'ascending' | 'descending' | undefined {
  if (key !== props.sort) return undefined
  return props.order === 'asc' ? 'ascending' : 'descending'
}

function share(item: ProgramSummary): string | null {
  const c = item.completions.value
  if (item.completions.status === 'unknown' || !c || c.nonresident === null || c.total === 0) return null
  return new Intl.NumberFormat(locale.value, { style: 'percent', maximumFractionDigits: 0 }).format(c.nonresident / c.total)
}
</script>

<template>
  <div class="table-wrap">
    <table class="programs-table" data-test="program-table">
      <caption class="visually-hidden">{{ t('programs.table.caption') }}</caption>
      <thead>
        <tr>
          <th v-for="col in COLUMNS" :key="col.key" scope="col" :aria-sort="ariaSort(col.key)" :class="{ numeric: col.numeric }">
            <button type="button" class="sort-button" :data-sort="col.key" @click="emit('sort', col.key)">
              {{ t(col.label) }}
              <span class="arrow" aria-hidden="true">{{ col.key === sort ? (order === 'asc' ? '↑' : '↓') : '↕' }}</span>
            </button>
          </th>
          <th scope="col">{{ t('programs.table.checks') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id" data-test="program-table-row">
          <td class="title-cell">
            <RouterLink :to="`/${prefix}/programs/${item.id}`">{{ item.title }}</RouterLink>
            <code class="cip">{{ item.cip.code }}</code>
          </td>
          <td>{{ item.institution.name }}<span class="sub">{{ item.campus.city ?? '—' }}</span></td>
          <td class="numeric"><TuitionPrice :tuition="item.graduate_tuition_nonresident" class="table-price" /></td>
          <td class="numeric">
            <template v-if="item.completions.value && item.completions.status !== 'unknown'">{{ formatNumber(item.completions.value.total, locale) }}</template>
            <StatusBadge v-else status="unknown" />
          </td>
          <td class="numeric">
            <template v-if="share(item) !== null">{{ share(item) }}</template>
            <StatusBadge v-else-if="item.completions.status === 'unknown' || item.completions.value?.nonresident == null" status="unknown" />
            <span v-else class="muted" :title="t('programs.table.noShare')">—<span class="visually-hidden">{{ t('programs.table.noShare') }}</span></span>
          </td>
          <td>
            <div class="checks">
            <span class="check"><span class="check-label">{{ t('programs.table.stem') }}</span> <StatusBadge :status="item.stem_opt.status" /><span class="visually-hidden">{{ t(stemKey(item.stem_opt)) }}</span></span>
            <span class="check"><span class="check-label">{{ t('programs.table.sevp') }}</span> <StatusBadge :status="item.sevp_status" /></span>
            <span class="check"><span class="check-label">{{ t('programs.table.accreditation') }}</span> <StatusBadge :status="item.accreditation_status" /></span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
.programs-table {
  inline-size: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
th,
td {
  padding-block: 0.5rem;
  padding-inline: 0.625rem;
  text-align: start;
  vertical-align: top;
  border-block-end: 1px solid var(--border);
}
tbody tr:last-child td {
  border-block-end: 0;
}
th {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  white-space: nowrap;
}
.numeric {
  text-align: end;
  font-variant-numeric: tabular-nums;
}
.sort-button {
  display: inline-flex;
  gap: 0.25rem;
  align-items: baseline;
  padding: 0;
  font: inherit;
  letter-spacing: inherit;
  text-transform: inherit;
  color: inherit;
  background: none;
  border: 0;
  cursor: pointer;
}
.sort-button:hover,
th[aria-sort] .sort-button {
  color: var(--text);
}
th[aria-sort] .arrow {
  color: var(--accent-text);
}
.title-cell a {
  color: var(--text);
  text-decoration-color: var(--accent-dim);
  font-weight: 600;
}
.title-cell a:hover {
  color: var(--accent-text);
}
.cip,
.sub {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
}
.table-price {
  justify-content: flex-end;
}
.muted {
  color: var(--text-muted);
}
.checks {
  display: grid;
  gap: 0.125rem;
}
.check {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  white-space: nowrap;
}
.check-label {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  color: var(--text-muted);
}
</style>
