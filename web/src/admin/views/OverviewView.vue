<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { get } from '../api'
import JobTable from '../components/JobTable.vue'
import ScheduleList from '../components/ScheduleList.vue'
import { count, dateTime } from '../format'
import type { Overview } from '../types'

const { t } = useI18n()
const data = ref<Overview | null>(null)
const failed = ref(false)

async function load() {
  failed.value = false
  try {
    data.value = await get<Overview>('/overview')
  } catch {
    failed.value = true
  }
}
onMounted(load)

const countries = computed(() => Object.entries(data.value?.countries ?? {}))
const TILES = [
  ['institutions', 'institutions'],
  ['institutions_accredited', 'accredited'],
  ['campuses_sevp_authorized', 'sevp'],
  ['programs', 'programs'],
  ['programs_stem_opt', 'stem'],
  ['programs_with_tuition', 'tuition'],
] as const
const openTasks = (tasks: Record<string, number>) =>
  Object.entries(tasks).map(([k, n]) => `${k}: ${n}`).join(', ')
</script>

<template>
  <section>
    <h1>{{ t('admin.overview.heading') }}</h1>
    <p v-if="failed" class="alert" role="alert">
      {{ t('admin.common.error') }} <button class="btn btn-small" type="button" @click="load">{{ t('admin.common.retry') }}</button>
    </p>
    <p v-else-if="!data" class="muted">{{ t('admin.common.loading') }}</p>
    <template v-else>
      <div class="row status-line">
        <span class="mono">
          {{ t('admin.overview.worker') }}:
          <strong>{{ data.worker.connected ? t('admin.overview.workerUp') : t('admin.overview.workerDown') }}</strong>
        </span>
        <span v-if="data.worker.last_heartbeat_at" class="mono muted">
          {{ t('admin.overview.lastHeartbeat', { at: dateTime(data.worker.last_heartbeat_at) }) }}
        </span>
        <RouterLink v-if="data.jobs_needing_attention" to="/admin/jobs?status=failed" class="mono">
          {{ t('admin.overview.attention', { n: data.jobs_needing_attention }) }}
        </RouterLink>
      </div>
      <p v-if="!data.worker.connected" class="note">{{ t('admin.overview.workerDownHelp') }}</p>
      <div class="row status-line">
        <span class="mono">
          {{ t('admin.overview.mail') }}:
          <strong>{{ data.mail.last_sent_at ? t('admin.overview.mailLast', { at: dateTime(data.mail.last_sent_at) }) : t('admin.overview.mailNever') }}</strong>
        </span>
        <span class="mono muted">{{ t('admin.overview.mailCounts', { sent: data.mail.sent_24h, queued: data.mail.queued, failed: data.mail.failed_24h }) }}</span>
      </div>
      <p v-if="data.mail.last_error" class="alert">{{ t('admin.overview.mailError', { error: data.mail.last_error }) }}</p>

      <template v-for="[country, c] in countries" :key="country">
        <h2>{{ t('admin.overview.country', { country }) }}</h2>
        <p v-if="!c.states.length" class="note">{{ t('admin.overview.noData') }}</p>
        <template v-else>
          <div class="tiles">
            <div class="tile">
              <span class="value">{{ count(c.total.states) }}</span>
              <span class="label">{{ t('admin.overview.states') }}</span>
            </div>
            <div v-for="[key, label] in TILES" :key="key" class="tile">
              <span class="value">{{ count(c.total[key]) }}</span>
              <span class="label">{{ t(`admin.overview.${label}`) }}</span>
            </div>
          </div>
          <details class="states">
            <summary class="mono">{{ t('admin.overview.scopes') }} ({{ c.states.length }})</summary>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{{ t('admin.overview.scopes') }}</th>
                    <th v-for="[key, label] in TILES" :key="key" class="num">{{ t(`admin.overview.${label}`) }}</th>
                    <th>{{ t('admin.overview.tasks') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in c.states" :key="s.scope">
                    <td class="mono">{{ s.scope }}</td>
                    <td v-for="[key] in TILES" :key="key" class="num">{{ count(s[key]) }}</td>
                    <td class="mono muted">{{ openTasks(s.open_tasks) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </details>
          <h2>{{ t('admin.overview.files') }}</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{{ t('admin.overview.source') }}</th>
                  <th>{{ t('admin.overview.version') }}</th>
                  <th>sha256</th>
                  <th class="num">{{ t('admin.overview.scopes') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(f, source) in c.source_files" :key="source">
                  <td class="mono">{{ source }}</td>
                  <td class="mono">{{ f.file_version }}</td>
                  <td class="mono muted">{{ f.sha256.slice(0, 12) }}</td>
                  <td class="num">{{ f.scopes }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </template>

      <h2>{{ t('admin.overview.schedules') }}</h2>
      <ScheduleList :schedules="data.schedules" @changed="load" />

      <h2>{{ t('admin.overview.recentJobs') }}</h2>
      <JobTable :jobs="data.jobs" />
      <p><RouterLink to="/admin/jobs">{{ t('admin.overview.allJobs') }}</RouterLink></p>
    </template>
  </section>
</template>

<style scoped>
.status-line {
  margin-block-end: 0.75rem;
}
.states {
  margin-block-start: 1rem;
}
.states summary {
  cursor: pointer;
  margin-block-end: 0.5rem;
}
</style>
