<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { rememberLocale } from '../i18n'
import { byCode, byPrefix, LOCALES } from '../locales'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const current = computed(() => byCode(locale.value)?.prefix ?? 'en')

function change(event: Event) {
  const target = byPrefix((event.target as HTMLSelectElement).value)
  if (!target) return
  rememberLocale(target)
  const rest = route.path.replace(/^\/[^/]+/, '') || '/'
  router.push(`/${target.prefix}${rest}`)
}
</script>

<template>
  <label class="switcher">
    <span class="label">{{ t('nav.language') }}</span>
    <select :value="current" @change="change">
      <option v-for="l in LOCALES" :key="l.code" :value="l.prefix" :lang="l.code">
        {{ l.name }}
      </option>
    </select>
  </label>
</template>

<style scoped>
.switcher {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
.label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}
select {
  font: inherit;
  font-size: 0.875rem;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding-block: 0.25rem;
  padding-inline: 0.5rem;
}
select:hover {
  border-color: var(--accent-dim);
}
</style>
