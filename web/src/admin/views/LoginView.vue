<script setup lang="ts">
// Two steps: password, then the authenticator code (when the account has one).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { AdminApiError, post } from '../api'
import { homeForStage, session } from '../session'
import type { SessionState } from '../types'

const { t } = useI18n()
const router = useRouter()
const username = ref('')
const password = ref('')
const code = ref('')
const busy = ref(false)
const error = ref('')

function message(e: unknown, invalidKey: string): string {
  if (e instanceof AdminApiError && e.status === 429) return t('admin.login.throttled')
  if (e instanceof AdminApiError && (e.status === 401 || e.status === 400)) return t(invalidKey)
  return t('admin.common.error')
}

async function after(state: SessionState) {
  session.set(state)
  if (state.stage !== 'totp') await router.replace(homeForStage(state.stage))
}

async function submitPassword() {
  error.value = ''
  busy.value = true
  try {
    await after(await post<SessionState>('/auth/login', { username: username.value, password: password.value }))
    password.value = ''
  } catch (e) {
    error.value = message(e, 'admin.login.invalid')
  } finally {
    busy.value = false
  }
}

async function submitCode() {
  error.value = ''
  busy.value = true
  try {
    await after(await post<SessionState>('/auth/totp', { code: code.value }))
  } catch (e) {
    code.value = ''
    if (e instanceof AdminApiError && e.status === 403) {
      // The pending session expired (5 minutes): start again.
      session.clear()
    }
    error.value = message(e, 'admin.login.invalidCode')
  } finally {
    busy.value = false
  }
}

function restart() {
  session.clear()
  error.value = ''
  code.value = ''
}
</script>

<template>
  <section class="login">
    <template v-if="session.stage !== 'totp'">
      <h1>{{ t('admin.login.heading') }}</h1>
      <form class="stack" @submit.prevent="submitPassword">
        <div>
          <label for="login-user">{{ t('admin.login.username') }}</label>
          <input id="login-user" v-model="username" type="text" autocomplete="username"
            autocapitalize="none" spellcheck="false" maxlength="64" required />
        </div>
        <div>
          <label for="login-password">{{ t('admin.login.password') }}</label>
          <input id="login-password" v-model="password" type="password" autocomplete="current-password" maxlength="256" required />
        </div>
        <p v-if="error" class="alert" role="alert">{{ error }}</p>
        <button class="btn btn-primary" type="submit" :disabled="busy">{{ t('admin.login.submit') }}</button>
      </form>
      <p class="forgot"><RouterLink to="/admin/forgot">{{ t('admin.login.forgot') }}</RouterLink></p>
    </template>
    <template v-else>
      <h1>{{ t('admin.login.totpHeading') }}</h1>
      <p>{{ t('admin.login.totpHelp') }}</p>
      <form class="stack" @submit.prevent="submitCode">
        <div>
          <label for="login-code">{{ t('admin.login.code') }}</label>
          <input id="login-code" v-model="code" class="code-input" type="text" inputmode="numeric"
            autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required autofocus />
        </div>
        <p v-if="error" class="alert" role="alert">{{ error }}</p>
        <div class="row">
          <button class="btn btn-primary" type="submit" :disabled="busy">{{ t('admin.login.verify') }}</button>
          <button class="btn" type="button" @click="restart">{{ t('admin.login.restart') }}</button>
        </div>
      </form>
    </template>
  </section>
</template>

<style scoped>
.login {
  max-inline-size: 24rem;
  margin-inline: auto;
  margin-block-start: 2rem;
}
.forgot {
  margin-block-start: 1rem;
  font-size: 0.875rem;
}
</style>
