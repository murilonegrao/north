import { createRouter, createWebHistory } from 'vue-router'
import { i18n, preferredLocale, setLocale } from './i18n'
import { byPrefix, LOCALES } from './locales'
import HomeView from './views/HomeView.vue'
import ProgramDetailView from './views/ProgramDetailView.vue'
import ProgramListView from './views/ProgramListView.vue'

const prefixes = LOCALES.map((l) => l.prefix).join('|')

export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: (to, from, saved) => saved ?? (to.path !== from.path ? { top: 0 } : undefined),
  routes: [
    { path: '/', redirect: () => `/${preferredLocale().prefix}/` },
    {
      path: `/:lang(${prefixes})/`,
      name: 'home',
      component: HomeView,
    },
    {
      path: `/:lang(${prefixes})/programs`,
      name: 'programs',
      component: ProgramListView,
      meta: { titleKey: 'programs.pageTitle', descriptionKey: 'programs.pageDescription' },
    },
    {
      // Stable URL per program (NFR-15): the id is `<unitid>-<cip6 without dot>`.
      path: `/:lang(${prefixes})/programs/:id`,
      name: 'program',
      component: ProgramDetailView,
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
  // The detail view replaces these with the program's own title once it has loaded.
  const titleKey = typeof to.meta.titleKey === 'string' ? to.meta.titleKey : 'meta.title'
  const descriptionKey = typeof to.meta.descriptionKey === 'string' ? to.meta.descriptionKey : 'meta.description'
  document.title = t(titleKey)
  document.querySelector('meta[name="description"]')?.setAttribute('content', t(descriptionKey))
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
