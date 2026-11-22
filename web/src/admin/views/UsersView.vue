<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { errorText, get, patch, post } from '../api'
import { dateTime } from '../format'
import { session } from '../session'
import type { AdminUser, Role } from '../types'

const { t } = useI18n()
const ROLES: Role[] = ['viewer', 'curator', 'admin']
const users = ref<AdminUser[]>([])
const error = ref('')
const notice = ref('')

async function load() {
  try {
    users.value = await get<AdminUser[]>('/users')
  } catch (e) {
    error.value = errorText(e)
  }
}
onMounted(load)

const form = ref({ username: '', role: 'viewer' as Role, password: '', email: '' })
async function create() {
  error.value = notice.value = ''
  try {
    const user = await post<AdminUser>('/users', form.value)
    notice.value = t('admin.users.created', { name: user.username })
    form.value = { username: '', role: 'viewer', password: '', email: '' }
    await load()
  } catch (e) {
    error.value = errorText(e)
  }
}

async function change(user: AdminUser, body: Record<string, unknown>) {
  error.value = notice.value = ''
  try {
    await patch(`/users/${user.id}`, body)
    notice.value = t('admin.users.resetDone')
    await load()
  } catch (e) {
    error.value = errorText(e)
  }
}

function resetPassword(user: AdminUser) {
  const pw = window.prompt(t('admin.users.newTemp', { name: user.username }))
  if (pw) void change(user, { reset_password: pw })
}

function setEmail(user: AdminUser) {
  const email = window.prompt(t('admin.users.setEmailPrompt', { name: user.username }), user.email ?? '')
  if (email) void change(user, { email })
}

function resetTotp(user: AdminUser) {
  if (window.confirm(`${t('admin.users.resetTotp')}: ${user.username}?`)) void change(user, { reset_totp: true })
}
</script>

<template>
  <section>
    <h1>{{ t('admin.users.heading') }}</h1>
    <p v-if="notice" class="note" role="status">{{ notice }}</p>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('admin.users.username') }}</th>
            <th>{{ t('admin.users.role') }}</th>
            <th>{{ t('admin.users.lastLogin') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="mono">
              {{ u.username }}
              <span v-if="u.id === session.user?.id" class="muted">({{ t('admin.users.you') }})</span>
              <div class="muted">
                <span v-if="u.disabled">{{ t('admin.users.disabled') }} · </span>
                {{ t('admin.users.totp') }}: {{ u.has_totp ? t('admin.common.yes') : t('admin.common.no') }}
              </div>
              <div v-if="u.email" class="muted">
                {{ u.email }}<span v-if="!u.email_verified"> ({{ t('admin.users.unverified') }})</span>
              </div>
            </td>
            <td>
              <select v-if="u.id !== session.user?.id" :value="u.role" :aria-label="t('admin.users.role')"
                @change="change(u, { role: ($event.target as HTMLSelectElement).value })">
                <option v-for="r in ROLES" :key="r" :value="r">{{ t(`admin.users.roles.${r}`) }}</option>
              </select>
              <span v-else class="mono">{{ t(`admin.users.roles.${u.role}`) }}</span>
            </td>
            <td class="mono">{{ dateTime(u.last_login_at) }}</td>
            <td>
              <div v-if="u.id !== session.user?.id" class="row">
                <button class="btn btn-small" type="button" @click="change(u, { disabled: !u.disabled })">
                  {{ u.disabled ? t('admin.users.enable') : t('admin.users.disable') }}
                </button>
                <button class="btn btn-small" type="button" @click="resetPassword(u)">{{ t('admin.users.resetPassword') }}</button>
                <button class="btn btn-small" type="button" :disabled="!u.has_totp" @click="resetTotp(u)">{{ t('admin.users.resetTotp') }}</button>
                <button class="btn btn-small" type="button" @click="setEmail(u)">{{ t('admin.users.setEmail') }}</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <h2>{{ t('admin.users.create') }}</h2>
    <p class="muted">{{ t('admin.users.roleHelp') }}</p>
    <form class="stack" @submit.prevent="create">
      <div>
        <label for="new-user">{{ t('admin.users.username') }}</label>
        <input id="new-user" v-model="form.username" type="text" autocomplete="off" autocapitalize="none" maxlength="64" required />
      </div>
      <div>
        <label for="new-role">{{ t('admin.users.role') }}</label>
        <select id="new-role" v-model="form.role">
          <option v-for="r in ROLES" :key="r" :value="r">{{ t(`admin.users.roles.${r}`) }}</option>
        </select>
      </div>
      <div>
        <label for="new-password">{{ t('admin.users.tempPassword') }}</label>
        <input id="new-password" v-model="form.password" type="password" autocomplete="new-password" minlength="12" maxlength="256" required />
      </div>
      <div>
        <label for="new-email">{{ t('admin.users.emailOptional') }}</label>
        <input id="new-email" v-model="form.email" type="email" autocomplete="off" maxlength="254" />
      </div>
      <button class="btn btn-primary" type="submit">{{ t('admin.users.createBtn') }}</button>
    </form>
  </section>
</template>
