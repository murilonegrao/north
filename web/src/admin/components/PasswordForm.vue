<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AdminApiError, errorText, post } from '../api'
import { session } from '../session'
import type { SessionState } from '../types'

const emit = defineEmits<{ done: [] }>()
const { t } = useI18n()
const current = ref('')
const next = ref('')
const again = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (next.value !== again.value) {
    error.value = t('admin.setup.mismatch')
    return
  }
  busy.value = true
  try {
    session.set(await post<SessionState>('/auth/password', { current: current.value, new: next.value }))
    current.value = next.value = again.value = ''
    emit('done')
  } catch (e) {
    const detail = e instanceof AdminApiError ? (e.detail as { field?: string }) : undefined
    error.value = detail?.field === 'current' ? t('admin.setup.wrongCurrent') : errorText(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="stack" @submit.prevent="submit">
    <div>
      <label for="pw-current">{{ t('admin.setup.current') }}</label>
      <input id="pw-current" v-model="current" type="password" autocomplete="current-password" required />
    </div>
    <div>
      <label for="pw-new">{{ t('admin.setup.new') }}</label>
      <input id="pw-new" v-model="next" type="password" autocomplete="new-password" minlength="12" maxlength="256" required />
    </div>
    <div>
      <label for="pw-again">{{ t('admin.setup.confirm') }}</label>
      <input id="pw-again" v-model="again" type="password" autocomplete="new-password" minlength="12" maxlength="256" required />
    </div>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <button class="btn btn-primary" type="submit" :disabled="busy">{{ t('admin.setup.save') }}</button>
  </form>
</template>
