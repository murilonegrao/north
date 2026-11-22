<script setup lang="ts">
// Asks for a reset link. The answer is the same whether or not the account exists.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AdminApiError, post } from '../api'

const { t } = useI18n()
const login = ref('')
const busy = ref(false)
const sent = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await post('/auth/forgot', { login: login.value })
    sent.value = true
  } catch (e) {
    error.value = e instanceof AdminApiError && e.status === 429 ? t('admin.login.throttled') : t('admin.common.error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="narrow">
    <h1>{{ t('admin.forgot.heading') }}</h1>
    <p v-if="sent" class="note" role="status">{{ t('admin.forgot.sent') }}</p>
    <form v-else class="stack" @submit.prevent="submit">
      <p class="muted">{{ t('admin.forgot.help') }}</p>
      <div>
        <label for="forgot-login">{{ t('admin.forgot.login') }}</label>
        <input id="forgot-login" v-model="login" type="text" autocomplete="username"
          autocapitalize="none" spellcheck="false" maxlength="254" required />
      </div>
      <p v-if="error" class="alert" role="alert">{{ error }}</p>
      <button class="btn btn-primary" type="submit" :disabled="busy">{{ t('admin.forgot.submit') }}</button>
    </form>
    <p><RouterLink to="/admin/login">{{ t('admin.forgot.back') }}</RouterLink></p>
  </section>
</template>

<style scoped>
.narrow {
  max-inline-size: 24rem;
  margin-inline: auto;
  margin-block-start: 2rem;
}
</style>
