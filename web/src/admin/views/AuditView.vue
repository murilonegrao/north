<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { errorText, get } from '../api'
import { dateTime } from '../format'
import type { AuditRow } from '../types'

const { t } = useI18n()
const rows = ref<AuditRow[]>([])
const error = ref('')
const more = ref(false)
const PAGE = 100

async function load(append = false) {
  try {
    const last = rows.value.at(-1)
    const qs = new URLSearchParams({ limit: String(PAGE) })
    if (append && last) qs.set('before', String(last.id))
    const page = await get<AuditRow[]>(`/audit?${qs}`)
    rows.value = append ? [...rows.value, ...page] : page
    more.value = page.length === PAGE
  } catch (e) {
    error.value = errorText(e)
  }
}
onMounted(() => load())
const detail = (d: Record<string, unknown>) => (Object.keys(d).length ? JSON.stringify(d) : '')
</script>

<template>
  <section>
    <h1>{{ t('admin.audit.heading') }}</h1>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('admin.audit.at') }}</th>
            <th>{{ t('admin.audit.actor') }}</th>
            <th>{{ t('admin.audit.action') }}</th>
            <th>{{ t('admin.audit.target') }}</th>
            <th>{{ t('admin.audit.detail') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td class="mono">{{ dateTime(r.at) }}</td>
            <td class="mono">{{ r.actor }}<div v-if="r.ip" class="muted">{{ r.ip }}</div></td>
            <td class="mono">{{ r.action }}</td>
            <td class="mono">{{ r.target ?? '' }}</td>
            <td class="mono muted detail">{{ detail(r.detail) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <button v-if="more" class="btn" type="button" @click="load(true)">{{ t('admin.audit.more') }}</button>
  </section>
</template>

<style scoped>
.detail {
  word-break: break-word;
  max-inline-size: 24rem;
}
</style>
