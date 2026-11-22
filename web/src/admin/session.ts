// The signed-in admin, shared by every admin view. The cookie is HttpOnly: the browser never
// sees the session token, only the CSRF token returned with the session state.
import { reactive } from 'vue'
import type { AdminUser, Role, SessionState, Stage } from './types'

interface Session {
  loaded: boolean
  user: AdminUser | null
  stage: Stage | null
  csrf: string
  set(state: SessionState): void
  clear(): void
  expire(): void
  can(role: Role): boolean
}

const RANK: Record<Role, number> = { viewer: 0, curator: 1, admin: 2 }

export const session = reactive<Session>({
  loaded: false,
  user: null,
  stage: null,
  csrf: '',
  set(state: SessionState) {
    this.user = state.user
    this.stage = state.stage
    this.csrf = state.csrf
    this.loaded = true
  },
  clear() {
    this.user = null
    this.stage = null
    this.csrf = ''
    this.loaded = true
  },
  /** The server said 401: forget the session; the router guard sends the user to sign in. */
  expire() {
    this.clear()
    expiredHandler?.()
  },
  can(role: Role) {
    return this.user !== null && this.stage === 'ok' && RANK[this.user.role] >= RANK[role]
  },
})

let expiredHandler: (() => void) | undefined
export function onSessionExpired(handler: () => void): void {
  expiredHandler = handler
}

/** Where a session in this stage belongs. */
export function homeForStage(stage: Stage | null): string {
  if (stage === null || stage === 'totp') return '/admin/login'
  if (stage === 'change_password' || stage === 'enroll_totp') return '/admin/setup'
  return '/admin'
}
