<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AdminApiError, errorText, patch, post } from '../api'
import PasswordForm from '../components/PasswordForm.vue'
import TotpEnroll from '../components/TotpEnroll.vue'
import { session } from '../session'
import type { SessionState } from '../types'

const { t } = useI18n()
const notice = ref('')
const error = ref('')
const replacing = ref(false)

const editingEmail = ref(false)
const newEmail = ref('')
const emailPassword = ref('')
const busy = ref(false)

function fail(e: unknown) {
  if (e instanceof AdminApiError && e.status === 429) error.value = t('admin.account.throttled')
  else if (e instanceof AdminApiError && (e.detail as { field?: string })?.field === 'password') error.value = t('admin.account.wrongPassword')
  else error.value = errorText(e)
}

async function run(action: () => Promise<void>) {
  notice.value = error.value = ''
  busy.value = true
  try {
    await action()
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}

const saveEmail = () =>
  run(async () => {
    session.set(await post<SessionState>('/auth/email', { email: newEmail.value, password: emailPassword.value }))
    notice.value = t('admin.account.emailSaved', { email: session.user?.email ?? '' })
    editingEmail.value = false
    newEmail.value = emailPassword.value = ''
  })

const resend = () =>
  run(async () => {
    await post('/auth/email/resend')
    notice.value = t('admin.account.emailSaved', { email: session.user?.email ?? '' })
  })

const testEmail = () =>
  run(async () => {
    const r = await post<{ to: string }>('/auth/email/test')
    notice.value = t('admin.account.testSent', { email: r.to })
  })

const setNotifyJobs = (value: boolean) =>
  run(async () => {
    session.set(await patch<SessionState>('/auth/preferences', { notify_jobs: value }))
  })
</script>

<template>
  <section>
    <h1>{{ t('admin.account.heading') }}</h1>
    <p v-if="session.user" class="muted">
      {{ t('admin.account.signedInAs', { name: session.user.username, role: t(`admin.users.roles.${session.user.role}`) }) }}
    </p>
    <p v-if="notice" class="note" role="status">{{ notice }}</p>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>

    <h2>{{ t('admin.account.email') }}</h2>
    <p class="muted">{{ t('admin.account.emailHelp') }}</p>
    <p v-if="session.user" class="mono">
      <template v-if="session.user.email">
        {{ session.user.email }} ·
        <strong>{{ session.user.email_verified ? t('admin.account.verified') : t('admin.account.unverified') }}</strong>
      </template>
      <template v-else>{{ t('admin.account.noEmail') }}</template>
    </p>
    <div class="row">
      <button v-if="!editingEmail" class="btn" type="button" @click="editingEmail = true">
        {{ session.user?.email ? t('admin.account.changeEmail') : t('admin.account.addEmail') }}
      </button>
      <button v-if="session.user?.email && !session.user.email_verified" class="btn" type="button" :disabled="busy" @click="resend">
        {{ t('admin.account.resend') }}
      </button>
      <button v-if="session.user?.email" class="btn" type="button" :disabled="busy" @click="testEmail">
        {{ t('admin.account.test') }}
      </button>
    </div>
    <form v-if="editingEmail" class="stack form-card" @submit.prevent="saveEmail">
      <div>
        <label for="acct-email">{{ t('admin.account.newEmail') }}</label>
        <input id="acct-email" v-model="newEmail" type="email" autocomplete="email" maxlength="254" required />
      </div>
      <div>
        <label for="acct-email-pw">{{ t('admin.account.confirmPassword') }}</label>
        <input id="acct-email-pw" v-model="emailPassword" type="password" autocomplete="current-password" maxlength="256" required />
      </div>
      <div class="row">
        <button class="btn btn-primary" type="submit" :disabled="busy">{{ t('admin.account.saveEmail') }}</button>
        <button class="btn" type="button" @click="editingEmail = false">{{ t('admin.account.cancel') }}</button>
      </div>
    </form>

    <h2>{{ t('admin.account.notifications') }}</h2>
    <p class="muted">{{ t('admin.account.notificationsHelp') }}</p>
    <label v-if="session.user" class="check">
      <input type="checkbox" :checked="session.user.notify_jobs" :disabled="busy"
        @change="setNotifyJobs(($event.target as HTMLInputElement).checked)" />
      {{ t('admin.account.notifyJobs') }}
    </label>

    <h2>{{ t('admin.account.password') }}</h2>
    <p class="muted">{{ t('admin.setup.passwordHelp') }}</p>
    <PasswordForm @done="notice = t('admin.setup.saved')" />
    <h2>{{ t('admin.account.totp') }}</h2>
    <button v-if="!replacing" class="btn" type="button" @click="replacing = true">{{ t('admin.account.replaceTotp') }}</button>
    <div v-else class="form-card">
      <TotpEnroll @done="replacing = false; notice = t('admin.setup.totpDone')" />
    </div>
  </section>
</template>

<style scoped>
.check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.check input {
  inline-size: auto;
}
.form-card {
  margin-block-start: 1rem;
}
</style>
