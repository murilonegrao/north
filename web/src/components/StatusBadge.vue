<script setup lang="ts">
// Verification status chip (BR-02, NFR-05). The five statuses differ by shape, glyph and word,
// not only by colour: A Forja allows a single accent, used only for confirmed_official.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { VerificationStatus } from '../api/types'

const props = defineProps<{ status: VerificationStatus }>()
const { t } = useI18n()

const GLYPHS: Record<VerificationStatus, string> = {
  confirmed_official: '✓',
  reported_by_program: '◇',
  extracted_unverified: '~',
  unknown: '?',
  confirmed_negative: '✕',
}

const glyph = computed(() => GLYPHS[props.status])
const short = computed(() => t(`badge.short.${props.status}`))
const description = computed(() => t(`badge.description.${props.status}`))
const label = computed(() => t('badge.aria', { status: t(`badge.long.${props.status}`) }))
</script>

<template>
  <span :class="['badge', `badge--${status}`]" :title="description" :data-status="status">
    <span class="glyph" aria-hidden="true">{{ glyph }}</span>
    <span aria-hidden="true">{{ short }}</span>
    <span class="visually-hidden">{{ label }}</span>
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3em;
  padding-block: 0.0625rem;
  padding-inline: 0.5rem;
  border: 1px solid transparent;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  line-height: 1.5;
  white-space: nowrap;
  vertical-align: middle;
  cursor: help;
}
.glyph {
  font-weight: 700;
}
/* Filled ember-dim chip: the only status that uses the accent. */
.badge--confirmed_official {
  background: var(--ember-dim);
  border-color: var(--ember-dim);
  color: var(--parchment);
}
/* Solid outline: the program says so on its own site. */
.badge--reported_by_program {
  border-color: var(--text-muted);
  color: var(--text);
}
/* Dashed outline: read by a machine, not yet checked by a person. */
.badge--extracted_unverified {
  border-style: dashed;
  border-color: var(--text-muted);
  color: var(--text);
}
/* Dotted, muted, square corners: nothing is known. Never looks like "No". */
.badge--unknown {
  border-style: dotted;
  border-color: var(--text-muted);
  border-radius: 2px;
  color: var(--text-muted);
  font-style: italic;
}
/* Solid neutral block: an official source says no. */
.badge--confirmed_negative {
  background: var(--text);
  border-color: var(--text);
  color: var(--bg);
  border-radius: 2px;
}
</style>
