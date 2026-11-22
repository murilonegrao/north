<script setup lang="ts">
// Confirms an address from the emailed link (#token=…). Works signed in or not.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { post } from '../api'
import { loadSession } from '../guard'
import { takeToken } from '../links'
import { session } from '../session'

const { t } = useI18n()
const state = ref<'working' | 'done' | 'invalid'>('working')
const email = ref('')

onMounted(async () => {
  const token = takeToken()
  if (!token) {
    state.value = 'invalid'
    return
  }
  try {
    email.value = (await post<{ email: string }>('/auth/email/verify', { token })).email
    state.value = 'done'
    if (session.stage === 'ok') await loadSession()
  } catch {
    state.value = 'invalid'
  }
})
</script>

<template>
  <section class="narrow">
    <h1>{{ t('admin.verify.heading') }}</h1>
    <p v-if="state === 'working'" class="muted">{{ t('admin.common.loading') }}</p>
    <p v-else-if="state === 'done'" class="note" role="status">{{ t('admin.verify.done', { email }) }}</p>
    <p v-else class="alert" role="alert">{{ t('admin.verify.invalid') }}</p>
    <p>
      <RouterLink :to="session.stage === 'ok' ? '/admin/account' : '/admin/login'">
        {{ session.stage === 'ok' ? t('admin.verify.toAccount') : t('admin.reset.toLogin') }}
      </RouterLink>
    </p>
  </section>
</template>

<style scoped>
.narrow {
  max-inline-size: 28rem;
  margin-inline: auto;
  margin-block-start: 2rem;
}
</style>
