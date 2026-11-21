<script setup lang="ts">
// One row of the detail page (FR-17): label, value, status badge, source link and date.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { VerificationStatus } from '../api/types'
import { formatDate, safeHttpUrl } from '../format'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{
  label: string
  status?: VerificationStatus
  sourceUrl?: string | null
  verifiedAt?: string | null
  evidence?: string | null
}>()

const { t, locale } = useI18n()
// Only http(s) URLs become links; anything else is shown as text (never a javascript: href).
const href = computed(() => safeHttpUrl(props.sourceUrl))
</script>

<template>
  <div class="field" :data-status="status">
    <dt>{{ label }}</dt>
    <dd>
      <div class="value-line">
        <span class="value"><slot /></span>
        <StatusBadge v-if="status" :status="status" />
      </div>
      <div class="meta">
        <a v-if="href" :href="href" target="_blank" rel="noopener noreferrer">
          {{ t('detail.meta.source') }}<span class="visually-hidden"> ({{ t('detail.meta.newTab') }})</span>
          <span aria-hidden="true">↗</span>
        </a>
        <span v-else-if="sourceUrl" class="source-text" data-test="source-text">{{ t('detail.meta.source') }}: {{ sourceUrl }}</span>
        <span v-else-if="status !== 'unknown'">{{ t('detail.meta.noSource') }}</span>
        <span v-if="verifiedAt">{{ t('detail.meta.checked', { date: formatDate(verifiedAt, locale) }) }}</span>
        <span v-if="evidence" class="evidence">{{ t('detail.meta.evidence') }}: <code>{{ evidence }}</code></span>
      </div>
      <slot name="note" />
    </dd>
  </div>
</template>

<style scoped>
.field {
  display: grid;
  grid-template-columns: minmax(10rem, 16rem) 1fr;
  gap: 0.25rem 1.25rem;
  padding-block: 0.75rem;
  border-block-end: 1px solid var(--border);
}
.field:last-child {
  border-block-end: 0;
}
dt {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
}
dd {
  margin: 0;
  min-inline-size: 0;
}
.value-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.625rem;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.125rem 1rem;
  margin-block-start: 0.25rem;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.source-text {
  overflow-wrap: anywhere;
}
.evidence code {
  font-size: 0.75rem;
  overflow-wrap: anywhere;
}
@media (max-width: 36rem) {
  .field {
    grid-template-columns: 1fr;
  }
}
</style>
