import { createRouter, createWebHistory } from 'vue-router'
import { i18n, preferredLocale, setLocale } from './i18n'
import { byPrefix, LOCALES } from './locales'
import HomeView from './views/HomeView.vue'

const prefixes = LOCALES.map((l) => l.prefix).join('|')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: () => `/${preferredLocale().prefix}/` },
    {
      path: `/:lang(${prefixes})/`,
      name: 'home',
      component: HomeView,
    },
    // Unknown paths go to the home page in the preferred language (until there is a 404 page).
    { path: '/:pathMatch(.*)*', redirect: () => `/${preferredLocale().prefix}/` },
  ],
})

router.beforeEach(async (to) => {
  const locale = byPrefix(to.params.lang as string | undefined)
  if (locale) await setLocale(locale)
})

router.afterEach((to) => {
  const t = i18n.global.t
  document.title = t('meta.title')
  document.querySelector('meta[name="description"]')?.setAttribute('content', t('meta.description'))
  updateAlternateLinks(to.path)
})

/** hreflang alternates for every wave-1 language (NFR-14, NFR-15). */
function updateAlternateLinks(path: string): void {
  document.head.querySelectorAll('link[data-hreflang]').forEach((el) => el.remove())
  const rest = path.replace(/^\/[^/]+/, '')
  const add = (hreflang: string, prefix: string) => {
    const link = document.createElement('link')
    link.rel = 'alternate'
    link.hreflang = hreflang
    link.href = `${window.location.origin}/${prefix}${rest}`
    link.dataset.hreflang = ''
    document.head.appendChild(link)
  }
  for (const l of LOCALES) add(l.code, l.prefix)
  add('x-default', 'en')
}
