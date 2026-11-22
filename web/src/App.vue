<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import SigilMark from './components/SigilMark.vue'
import { byCode } from './locales'
import { theme, toggleTheme } from './theme'

const { t, locale } = useI18n()
const prefix = computed(() => byCode(locale.value)?.prefix ?? 'en')
const homePath = computed(() => `/${prefix.value}/`)
const programsPath = computed(() => `/${prefix.value}/programs`)
const route = useRoute()
const inPrograms = computed(() => route.path.startsWith(programsPath.value))
const placementPath = computed(() => `/${prefix.value}/placement`)
const inPlacement = computed(() => route.path.startsWith(placementPath.value))
const themeLabel = computed(() => (theme.value === 'dark' ? t('theme.toLight') : t('theme.toDark')))
// The admin area has its own layout (AdminShell): no public header, notice or footer.
const isAdmin = computed(() => route.meta.admin === true)
</script>

<template>
  <RouterView v-if="isAdmin" />
  <template v-else>
  <a class="skip-link" href="#main">{{ t('nav.skip') }}</a>
  <header class="site-header">
    <div class="container header-row">
      <RouterLink :to="homePath" class="brand" :aria-label="t('nav.home')">
        <SigilMark :size="24" />
        <span>North</span>
      </RouterLink>
      <nav class="site-nav" :aria-label="t('nav.main')">
        <RouterLink :to="programsPath" :class="['nav-link', { active: inPrograms }]" :aria-current="inPrograms ? 'page' : undefined">{{ t('nav.programs') }}</RouterLink>
        <RouterLink :to="placementPath" :class="['nav-link', { active: inPlacement }]" :aria-current="inPlacement ? 'page' : undefined">{{ t('nav.placement') }}</RouterLink>
      </nav>
      <div class="header-tools">
        <LanguageSwitcher />
        <button type="button" class="theme-toggle" :aria-label="themeLabel" :title="themeLabel" @click="toggleTheme">
          {{ theme === 'dark' ? t('theme.light') : t('theme.dark') }}
        </button>
      </div>
    </div>
  </header>

  <!-- NFR-11: the notice is part of the layout, so it is on every page. -->
  <div class="container">
    <aside class="disclaimer" role="note">{{ t('disclaimer') }}</aside>
  </div>

  <main id="main" class="container">
    <RouterView />
  </main>

  <footer class="site-footer">
    <div class="container footer-row">
      <SigilMark :size="20" />
      <span>{{ t('footer.license') }}</span>
    </div>
  </footer>
  </template>
</template>

<style scoped>
.skip-link {
  position: absolute;
  inset-inline-start: 1rem;
  inset-block-start: -3rem;
  padding-block: 0.5rem;
  padding-inline: 0.75rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  z-index: 10;
}
.skip-link:focus {
  inset-block-start: 1rem;
}
.site-header {
  border-block-end: 1px solid var(--border);
}
.header-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1.5rem;
  padding-block: 0.875rem;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.625rem;
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--text);
  text-decoration: none;
}
.site-nav {
  flex: 1;
  display: flex;
  gap: 1rem;
}
.nav-link {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  color: var(--text-muted);
  text-decoration: none;
  padding-block: 0.25rem;
  border-block-end: 2px solid transparent;
}
.nav-link:hover {
  color: var(--text);
}
.nav-link.active {
  color: var(--text);
  border-block-end-color: var(--accent);
}
.header-tools {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.theme-toggle {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding-block: 0.375rem;
  padding-inline: 0.625rem;
  cursor: pointer;
}
.theme-toggle:hover {
  color: var(--text);
  border-color: var(--accent-dim);
}
.disclaimer {
  margin-block-start: 1.5rem;
  padding-block: 0.625rem;
  padding-inline: 0.875rem;
  border-inline-start: 2px solid var(--accent-dim);
  background: var(--surface);
  border-radius: var(--radius);
  font-size: 0.875rem;
  color: var(--text-muted);
}
main {
  flex: 1;
  padding-block: 2.5rem 3rem;
}
.site-footer {
  border-block-start: 1px solid var(--border);
  color: var(--text-muted);
}
.footer-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding-block: 1.25rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
}
</style>
