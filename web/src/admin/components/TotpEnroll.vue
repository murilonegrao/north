<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { errorText, post } from '../api'
import { session } from '../session'
import type { SessionState } from '../types'

const emit = defineEmits<{ done: [] }>()
const { t } = useI18n()
const setup = ref<{ secret: string; qr: string } | null>(null)
const code = ref('')
const busy = ref(false)
const error = ref('')

async function start() {
  error.value = ''
  busy.value = true
  try {
    setup.value = await post<{ secret: string; qr: string }>('/auth/totp/setup')
  } catch (e) {
    error.value = errorText(e)
  } finally {
    busy.value = false
  }
}

async function confirm() {
  error.value = ''
  busy.value = true
  try {
    session.set(await post<SessionState>('/auth/totp/confirm', { code: code.value }))
    setup.value = null
    code.value = ''
    emit('done')
  } catch {
    error.value = t('admin.login.invalidCode')
  } finally {
    busy.value = false
  }
}

const grouped = (s: string) => s.match(/.{1,4}/g)?.join(' ') ?? s
</script>

<template>
  <div class="stack">
    <p>{{ t('admin.setup.totpHelp') }}</p>
    <button v-if="!setup" class="btn btn-primary" type="button" :disabled="busy" @click="start">
      {{ t('admin.setup.start') }}
    </button>
    <template v-else>
      <img class="qr" :src="setup.qr" alt="" width="220" height="220" />
      <p>
        <span class="muted">{{ t('admin.setup.secret') }}:</span>{{ ' ' }}<code class="secret">{{ grouped(setup.secret) }}</code>
      </p>
      <form class="stack" @submit.prevent="confirm">
        <div>
          <label for="totp-code">{{ t('admin.login.code') }}</label>
          <input id="totp-code" v-model="code" class="code-input" type="text" inputmode="numeric"
            autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required />
        </div>
        <button class="btn btn-primary" type="submit" :disabled="busy">{{ t('admin.setup.confirm2') }}</button>
      </form>
    </template>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.qr {
  display: block;
  background: var(--parchment); /* QR needs a light quiet zone in both themes */
  border-radius: var(--radius);
  padding: 0.5rem;
}
.secret {
  word-break: break-all;
}
</style>
