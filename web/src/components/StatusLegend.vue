<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { VERIFICATION_STATUSES } from '../api/types'
import StatusBadge from './StatusBadge.vue'

const { t } = useI18n()
</script>

<template>
  <details class="legend" open>
    <summary>{{ t('legend.title') }}</summary>
    <ul>
      <li v-for="status in VERIFICATION_STATUSES" :key="status">
        <StatusBadge :status="status" />
        <span>{{ t(`badge.description.${status}`) }}</span>
      </li>
    </ul>
  </details>
</template>

<style scoped>
.legend {
  font-size: 0.8125rem;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding-block: 0.5rem;
  padding-inline: 0.875rem;
}
summary {
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text);
}
ul {
  list-style: none;
  margin: 0;
  margin-block-start: 0.5rem;
  padding: 0;
  display: grid;
  gap: 0.375rem;
}
li {
  display: grid;
  grid-template-columns: 8.5rem 1fr;
  align-items: start;
  gap: 0.75rem;
}
li > :first-child {
  justify-self: start;
}
@media (max-width: 30rem) {
  li {
    grid-template-columns: 1fr;
    gap: 0.125rem;
  }
}
</style>
