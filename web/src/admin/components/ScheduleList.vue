<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { AdminApiError, errorText, patch, post } from '../api'
import { dateTime, kindText, params } from '../format'
import { session } from '../session'
import type { Job, ScheduleRow } from '../types'

defineProps<{ schedules: ScheduleRow[] }>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const router = useRouter()
const error = ref('')

async function toggle(row: ScheduleRow) {
  error.value = ''
  try {
    await patch(`/schedules/${row.id}`, { paused: !row.paused })
    emit('changed')
  } catch (e) {
    error.value = errorText(e)
  }
}

async function runNow(row: ScheduleRow) {
  error.value = ''
  try {
    const job = await post<Job>(`/schedules/${row.id}/run`)
    await router.push(`/admin/jobs/${job.id}`)
  } catch (e) {
    if (e instanceof AdminApiError && e.status === 409) {
      await router.push(`/admin/jobs/${String(e.body.job_id)}`)
      return
    }
    error.value = errorText(e)
  }
}
</script>

<template>
  <div class="table-wrap">
    <table>
      <tbody>
        <tr v-for="row in schedules" :key="row.id">
          <td>
            <strong>{{ kindText(row.kind, 'title', row.title) }}</strong>
            <div class="mono muted">{{ row.id }} · {{ params(row.params) }}</div>
          </td>
          <td class="mono">
            {{ t('admin.schedule.every', { h: row.every_hours }) }}<br />
            <span v-if="row.paused" class="muted">{{ t('admin.schedule.paused') }}</span>
            <span v-else>{{ t('admin.schedule.next', { at: dateTime(row.next_run_at) }) }}</span>
          </td>
          <td>
            <div class="row">
              <button v-if="session.can('curator')" class="btn btn-small" type="button" @click="runNow(row)">{{ t('admin.schedule.runNow') }}</button>
              <button v-if="session.can('admin')" class="btn btn-small" type="button" @click="toggle(row)">
                {{ row.paused ? t('admin.schedule.resume') : t('admin.schedule.pause') }}
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-if="error" class="alert" role="alert">{{ error }}</p>
</template>
