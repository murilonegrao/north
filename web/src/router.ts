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
    {
      // Admin area (record 0006): lazy chunk, never indexed, its own layout.
      path: '/admin',
      component: () => import('./admin/AdminShell.vue'),
      meta: { admin: true },
      children: [
        { path: '', name: 'admin-overview', component: () => import('./admin/views/OverviewView.vue'), meta: { titleKey: 'admin.title.overview' } },
        { path: 'login', name: 'admin-login', component: () => import('./admin/views/LoginView.vue'), meta: { titleKey: 'admin.title.login' } },
        { path: 'setup', name: 'admin-setup', component: () => import('./admin/views/SetupView.vue'), meta: { titleKey: 'admin.title.setup' } },
        { path: 'jobs', name: 'admin-jobs', component: () => import('./admin/views/JobsView.vue'), meta: { titleKey: 'admin.title.jobs' } },
        { path: 'jobs/:id(\\d+)', name: 'admin-job', component: () => import('./admin/views/JobView.vue'), meta: { titleKey: 'admin.title.job' } },
        { path: 'upload', name: 'admin-upload', component: () => import('./admin/views/UploadView.vue'), meta: { titleKey: 'admin.title.upload', minRole: 'curator' } },
        { path: 'users', name: 'admin-users', component: () => import('./admin/views/UsersView.vue'), meta: { titleKey: 'admin.title.users', minRole: 'admin' } },
        { path: 'audit', name: 'admin-audit', component: () => import('./admin/views/AuditView.vue'), meta: { titleKey: 'admin.title.audit', minRole: 'admin' } },
        { path: 'account', name: 'admin-account', component: () => import('./admin/views/AccountView.vue'), meta: { titleKey: 'admin.title.account' } },
        { path: ':rest(.*)*', redirect: '/admin' },
      ],
    },
    // Unknown paths go to the home page in the preferred language (until there is a 404 page).
    { path: '/:pathMatch(.*)*', redirect: () => `/${preferredLocale().prefix}/` },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.admin) {
    // Loaded on demand: the public bundle carries none of the admin code.
    const { adminGuard } = await import('./admin/guard')
    return adminGuard(to)
  }
  const locale = byPrefix(to.params.lang as string | undefined)
  if (locale) await setLocale(locale)
  return true
})

router.afterEach((to) => {
  const t = i18n.global.t
  // The detail view replaces these with the program's own title once it has loaded.
  const titleKey = typeof to.meta.titleKey === 'string' ? to.meta.titleKey : 'meta.title'
  const descriptionKey = typeof to.meta.descriptionKey === 'string' ? to.meta.descriptionKey : 'meta.description'
  setRobots(Boolean(to.meta.admin))
  if (to.meta.admin) {
    document.title = `${t(titleKey)} · North admin`
    document.head.querySelectorAll('link[data-hreflang]').forEach((el) => el.remove())
    return
  }
  document.title = t(titleKey)
  document.querySelector('meta[name="description"]')?.setAttribute('content', t(descriptionKey))
  updateAlternateLinks(to.path)
})

/** noindex on admin pages (the server also sends X-Robots-Tag). */
function setRobots(noindex: boolean): void {
  let tag = document.head.querySelector<HTMLMetaElement>('meta[name="robots"][data-admin]')
  if (!noindex) {
    tag?.remove()
    return
  }
  if (!tag) {
    tag = document.createElement('meta')
    tag.name = 'robots'
    tag.dataset.admin = ''
    document.head.appendChild(tag)
  }
  tag.content = 'noindex, nofollow'
}

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
