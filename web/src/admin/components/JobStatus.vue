<script setup lang="ts">
// Job status chip. Like the public verification badges, statuses differ by glyph and word,
// not by colour; the single accent marks only what is happening now (running).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { JobStatus } from '../types'

const props = defineProps<{ status: JobStatus }>()
const { t } = useI18n()
const GLYPHS: Record<JobStatus, string> = {
  queued: '…',
  running: '▸',
  succeeded: '✓',
  attention: '!',
  failed: '✕',
  cancelled: '–',
}
const glyph = computed(() => GLYPHS[props.status])
</script>

<template>
  <span :class="['job-status', `job-status--${status}`]">
    <span aria-hidden="true" class="glyph">{{ glyph }}</span>
    {{ t(`admin.status.${status}`) }}
  </span>
</template>

<style scoped>
.job-status {
  display: inline-flex;
  align-items: center;
  gap: 0.35em;
  padding-block: 0.0625rem;
  padding-inline: 0.5rem;
  border: 1px solid var(--text-muted);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  white-space: nowrap;
  color: var(--text);
}
.glyph {
  font-weight: 700;
}
.job-status--queued,
.job-status--cancelled {
  border-style: dotted;
  color: var(--text-muted);
}
.job-status--running {
  border-color: var(--accent);
}
.job-status--attention {
  border-style: dashed;
}
.job-status--failed {
  background: var(--text);
  border-color: var(--text);
  color: var(--bg);
  border-radius: 2px;
}
</style>
