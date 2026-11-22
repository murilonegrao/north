<script setup lang="ts">
// New password from an emailed link (#token=…). The authenticator code is still asked at sign-in.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AdminApiError, errorText, post } from '../api'
import { takeToken } from '../links'
import { session } from '../session'

const { t } = useI18n()
const token = ref('')
const next = ref('')
const again = ref('')
const busy = ref(false)
const done = ref(false)
const badLink = ref(false)
const error = ref('')

onMounted(() => {
  token.value = takeToken()
  badLink.value = !token.value
})

async function submit() {
  error.value = ''
  if (next.value !== again.value) {
    error.value = t('admin.setup.mismatch')
    return
  }
  busy.value = true
  try {
    await post('/auth/reset', { token: token.value, new: next.value })
    next.value = again.value = ''
    done.value = true
    session.clear() // every session of the account ended on the server
  } catch (e) {
    const field = e instanceof AdminApiError ? (e.detail as { field?: string })?.field : undefined
    if (field === 'token') badLink.value = true
    else error.value = errorText(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="narrow">
    <h1>{{ t('admin.reset.heading') }}</h1>
    <template v-if="done">
      <p class="note" role="status">{{ t('admin.reset.done') }}</p>
      <p><RouterLink to="/admin/login">{{ t('admin.reset.toLogin') }}</RouterLink></p>
    </template>
    <template v-else-if="badLink">
      <p class="alert" role="alert">{{ t('admin.reset.invalid') }}</p>
      <p><RouterLink to="/admin/forgot">{{ t('admin.reset.again') }}</RouterLink></p>
    </template>
    <form v-else class="stack" @submit.prevent="submit">
      <p class="muted">{{ t('admin.setup.passwordHelp') }}</p>
      <div>
        <label for="reset-new">{{ t('admin.setup.new') }}</label>
        <input id="reset-new" v-model="next" type="password" autocomplete="new-password" minlength="12" maxlength="256" required />
      </div>
      <div>
        <label for="reset-again">{{ t('admin.setup.confirm') }}</label>
        <input id="reset-again" v-model="again" type="password" autocomplete="new-password" minlength="12" maxlength="256" required />
      </div>
      <p v-if="error" class="alert" role="alert">{{ error }}</p>
      <button class="btn btn-primary" type="submit" :disabled="busy">{{ t('admin.setup.save') }}</button>
    </form>
  </section>
</template>

<style scoped>
.narrow {
  max-inline-size: 24rem;
  margin-inline: auto;
  margin-block-start: 2rem;
}
</style>
