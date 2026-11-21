<script setup lang="ts">
// Graduate tuition (nonresident) in a list card or table cell (contract v0.2 §1).
// The amount is an institution-wide average, so a short qualifier is always visible and the
// full note is a tooltip (hover or keyboard focus) that screen readers also get. Unknown is
// shown as Unknown with its badge, never as $0 (BR-02).
import { computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import type { TuitionValue } from '../api/types'
import { formatMoney } from '../format'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{ tuition: TuitionValue }>()
const { t, locale } = useI18n()
const noteId = useId()

const known = computed(() => props.tuition.status !== 'unknown' && props.tuition.value !== null)
const amount = computed(() => (props.tuition.value ? formatMoney(props.tuition.value, locale.value) : ''))
const noteCode = computed(() => props.tuition.note_code ?? null)
</script>

<template>
  <span class="price" data-test="tuition" :data-status="tuition.status">
    <template v-if="known">
      <span class="amount">{{ t('price.perYear', { amount }) }}</span>
      <StatusBadge :status="tuition.status" />
      <span v-if="noteCode" class="qualifier-wrap">
        <span class="qualifier" tabindex="0" :aria-describedby="noteId">{{ t(`price.qualifier.${noteCode}`) }}</span>
        <span :id="noteId" role="tooltip" class="tip">{{ t(`detail.notes.${noteCode}`) }}</span>
      </span>
    </template>
    <template v-else>
      <span class="muted">{{ t('detail.values.unknown') }}</span>
      <StatusBadge status="unknown" />
    </template>
  </span>
</template>

<style scoped>
.price {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
}
.amount {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  white-space: nowrap;
}
.muted {
  color: var(--text-muted);
}
.qualifier-wrap {
  position: relative;
  display: inline-flex;
}
.qualifier {
  font-size: 0.8125rem;
  color: var(--text-muted);
  text-decoration: underline dotted;
  text-underline-offset: 0.2em;
  cursor: help;
  white-space: nowrap;
}
.tip {
  position: absolute;
  inset-block-end: calc(100% + 0.375rem);
  inset-inline-start: 0;
  z-index: 10;
  inline-size: max-content;
  max-inline-size: min(18rem, 80vw);
  padding-block: 0.375rem;
  padding-inline: 0.625rem;
  font-size: 0.8125rem;
  line-height: 1.4;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--text-muted);
  border-radius: var(--radius);
  visibility: hidden;
  opacity: 0;
}
.qualifier-wrap:hover .tip,
.qualifier:focus-visible + .tip {
  visibility: visible;
  opacity: 1;
}
</style>
