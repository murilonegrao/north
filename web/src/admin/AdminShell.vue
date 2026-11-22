<script setup lang="ts">
// Admin layout: its own header and navigation, no public notice. Signed-out pages (login,
// setup) get only the brand.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import SigilMark from '../components/SigilMark.vue'
import { theme, toggleTheme } from '../theme'
import './admin.css'
import { post } from './api'
import { installAdminExpiry, useAdminLocale } from './guard'
import { ADMIN_LOCALES } from './i18n'
import { session } from './session'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
installAdminExpiry(router)

const signedIn = computed(() => session.stage === 'ok')
const links = computed(() =>
  [
    { to: '/admin', key: 'overview', exact: true, show: true },
    { to: '/admin/jobs', key: 'jobs', exact: false, show: true },
    { to: '/admin/upload', key: 'upload', exact: false, show: session.can('curator') },
    { to: '/admin/users', key: 'users', exact: false, show: session.can('admin') },
    { to: '/admin/audit', key: 'audit', exact: false, show: session.can('admin') },
    { to: '/admin/account', key: 'account', exact: false, show: true },
  ].filter((l) => l.show),
)
const isActive = (to: string, exact: boolean) => (exact ? route.path === to : route.path.startsWith(to))

async function logout() {
  try {
    await post('/auth/logout')
  } finally {
    session.clear()
    await router.push('/admin/login')
  }
}

async function changeLocale(event: Event) {
  await useAdminLocale((event.target as HTMLSelectElement).value)
}
</script>

<template>
  <div class="admin">
    <a class="skip-link" href="#admin-main">{{ t('nav.skip') }}</a>
    <header class="admin-header">
      <div class="container header-row">
        <RouterLink to="/admin" class="brand">
          <SigilMark :size="22" />
          <span>{{ t('admin.brand') }}</span>
        </RouterLink>
        <nav v-if="signedIn" class="admin-nav" :aria-label="t('admin.nav.main')">
          <RouterLink
            v-for="link in links"
            :key="link.key"
            :to="link.to"
            :class="['nav-link', { active: isActive(link.to, link.exact) }]"
            :aria-current="isActive(link.to, link.exact) ? 'page' : undefined"
          >{{ t(`admin.nav.${link.key}`) }}</RouterLink>
        </nav>
        <div class="tools">
          <label class="visually-hidden" for="admin-locale">{{ t('admin.nav.language') }}</label>
          <select id="admin-locale" class="locale" :value="locale" @change="changeLocale">
            <option v-for="l in ADMIN_LOCALES" :key="l.code" :value="l.code">{{ l.name }}</option>
          </select>
          <button type="button" class="tool" @click="toggleTheme">
            {{ theme === 'dark' ? t('theme.light') : t('theme.dark') }}
          </button>
          <span v-if="session.user && signedIn" class="who mono">{{ session.user.username }}</span>
          <button v-if="session.user" type="button" class="tool" @click="logout">{{ t('admin.nav.logout') }}</button>
          <a href="/" class="tool">{{ t('admin.nav.site') }}</a>
        </div>
      </div>
    </header>
    <main id="admin-main" class="container admin-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.admin {
  display: flex;
  flex-direction: column;
  flex: 1;
}
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
.admin-header {
  border-block-end: 1px solid var(--border);
  background: var(--surface);
}
.header-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.5rem;
  padding-block: 0.75rem;
  max-inline-size: 72rem;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--text);
  text-decoration: none;
}
.admin-nav {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
}
.nav-link {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
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
.tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-inline-start: auto;
}
.locale {
  inline-size: auto;
}
.tool,
.locale {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding-block: 0.3125rem;
  padding-inline: 0.5rem;
  text-decoration: none;
  cursor: pointer;
}
.tool:hover {
  color: var(--text);
  border-color: var(--accent-dim);
}
.who {
  color: var(--text);
}
.admin-main {
  flex: 1;
  max-inline-size: 72rem;
  padding-block: 2rem 3rem;
}
</style>
