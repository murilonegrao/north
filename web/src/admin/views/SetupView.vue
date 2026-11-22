<script setup lang="ts">
// Forced on first sign-in: a new password, then an authenticator app.
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import PasswordForm from '../components/PasswordForm.vue'
import TotpEnroll from '../components/TotpEnroll.vue'
import { homeForStage, session } from '../session'

const { t } = useI18n()
const router = useRouter()

async function next() {
  if (session.stage === 'ok') await router.replace(homeForStage('ok'))
}
</script>

<template>
  <section class="setup">
    <h1>{{ t('admin.title.setup') }}</h1>
    <template v-if="session.stage === 'change_password'">
      <h2>{{ t('admin.setup.passwordHeading') }}</h2>
      <p class="muted">{{ t('admin.setup.passwordHelp') }}</p>
      <PasswordForm @done="next" />
    </template>
    <template v-else-if="session.stage === 'enroll_totp'">
      <h2>{{ t('admin.setup.totpHeading') }}</h2>
      <TotpEnroll @done="next" />
    </template>
  </section>
</template>

<style scoped>
.setup {
  max-inline-size: 30rem;
  margin-inline: auto;
}
</style>
