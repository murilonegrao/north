<script setup lang="ts">
// North sigil (A Forja grammar): ring in the text colour, needle glyph in ember.
// Signature only: favicon, header mark, footer seal. Never a hero.
withDefaults(defineProps<{ size?: number }>(), { size: 24 })
</script>

<template>
  <svg
    class="sigil"
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    fill="none"
    stroke-width="3"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <circle cx="50" cy="50" r="42" stroke="currentColor" />
    <path d="M38 42 L50 28 L62 42" class="sigil-glyph" />
    <line x1="50" y1="28" x2="50" y2="72" class="sigil-glyph" />
    <circle cx="50" cy="72" r="4" class="sigil-node" />
  </svg>
</template>

<style scoped>
.sigil {
  display: block;
  flex: none;
}
.sigil-glyph {
  stroke: var(--accent);
}
.sigil-node {
  fill: var(--accent);
}
</style>
