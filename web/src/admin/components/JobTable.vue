<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { dateTime, duration, kindText, params } from '../format'
import type { Job } from '../types'
import JobStatus from './JobStatus.vue'

defineProps<{ jobs: Job[] }>()
const { t } = useI18n()
</script>

<template>
  <p v-if="jobs.length === 0" class="muted">{{ t('admin.jobs.empty') }}</p>
  <div v-else class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>{{ t('admin.jobs.kind') }}</th>
          <th>{{ t('admin.jobs.status') }}</th>
          <th>{{ t('admin.jobs.by') }}</th>
          <th>{{ t('admin.jobs.created') }}</th>
          <th class="num">{{ t('admin.jobs.duration') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in jobs" :key="job.id">
          <td class="mono"><RouterLink :to="`/admin/jobs/${job.id}`">#{{ job.id }}</RouterLink></td>
          <td>
            {{ kindText(job.kind, 'title', job.title) }}
            <div v-if="Object.keys(job.params).length" class="mono muted">{{ params(job.params) }}</div>
          </td>
          <td><JobStatus :status="job.status" /></td>
          <td class="mono">{{ job.requested_by ?? t('admin.jobs.scheduler') }}</td>
          <td class="mono">{{ dateTime(job.created_at) }}</td>
          <td class="num mono">{{ duration(job.started_at, job.finished_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
