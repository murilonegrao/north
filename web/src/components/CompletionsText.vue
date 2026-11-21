<script setup lang="ts">
// Graduates line ("12 total / 8 nonresident (2023-24)"). A missing nonresident count is shown
// as Unknown with its badge, never as 0 (BR-02); missing completions as "No completions data".
import { useI18n } from 'vue-i18n'
import type { Completions } from '../api/types'
import { formatNumber } from '../format'
import StatusBadge from './StatusBadge.vue'

defineProps<{ completions: Completions }>()
const { t, locale } = useI18n()
const num = (n: number) => formatNumber(n, locale.value)
</script>

<template>
  <span v-if="completions.value && completions.status !== 'unknown'" class="completions" data-test="completions">
    <template v-if="completions.value.nonresident !== null">
      {{ t('program.completionsValue', { total: num(completions.value.total), nonresident: num(completions.value.nonresident), year: completions.value.year }) }}
    </template>
    <template v-else>
      {{ t('program.completionsTotalOnly', { total: num(completions.value.total), year: completions.value.year }) }}
      <span class="nonresident-unknown" data-test="nonresident-unknown">
        {{ t('program.nonresidentLabel') }} <span class="muted">{{ t('detail.values.unknown') }}</span>
        <StatusBadge status="unknown" />
      </span>
    </template>
  </span>
  <span v-else class="muted">{{ t('program.completionsNone') }}</span>
</template>

<style scoped>
.nonresident-unknown {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  margin-inline-start: 0.25rem;
}
.muted {
  color: var(--text-muted);
}
</style>
