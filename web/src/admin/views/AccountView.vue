<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import PasswordForm from '../components/PasswordForm.vue'
import TotpEnroll from '../components/TotpEnroll.vue'
import { session } from '../session'

const { t } = useI18n()
const notice = ref('')
const replacing = ref(false)
</script>

<template>
  <section>
    <h1>{{ t('admin.account.heading') }}</h1>
    <p v-if="session.user" class="muted">
      {{ t('admin.account.signedInAs', { name: session.user.username, role: t(`admin.users.roles.${session.user.role}`) }) }}
    </p>
    <p v-if="notice" class="note" role="status">{{ notice }}</p>
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
