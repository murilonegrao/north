<script setup lang="ts">
// One job: parameters, live log (polled every 2 s while it runs), result, cancel.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { errorText, get, post } from '../api'
import JobStatus from '../components/JobStatus.vue'
import { dateTime, duration, kindText, params } from '../format'
import { session } from '../session'
import type { JobDetail } from '../types'

const { t } = useI18n()
const route = useRoute()
const id = computed(() => Number(route.params.id))
const job = ref<JobDetail | null>(null)
const lines = ref<string[]>([])
const error = ref('')
const logEl = ref<HTMLPreElement | null>(null)
let lastLogId = 0
let timer: number | undefined

const active = computed(() => job.value?.status === 'queued' || job.value?.status === 'running')

async function poll() {
  try {
    const data = await get<JobDetail>(`/jobs/${id.value}?after=${lastLogId}`)
    const atBottom = logEl.value ? logEl.value.scrollHeight - logEl.value.scrollTop - logEl.value.clientHeight < 40 : true
    if (data.logs.length) {
      lines.value.push(...data.logs.map((l) => l.line))
      lastLogId = data.logs.at(-1)!.id
    }
    job.value = data
    error.value = ''
    if (atBottom) {
      await nextTick()
      logEl.value?.scrollTo({ top: logEl.value.scrollHeight })
    }
  } catch (e) {
    error.value = errorText(e)
  }
  timer = active.value || !job.value ? window.setTimeout(poll, 2000) : undefined
}

onMounted(poll)
onBeforeUnmount(() => window.clearTimeout(timer))

async function cancel() {
  try {
    await post(`/jobs/${id.value}/cancel`)
    window.clearTimeout(timer)
    await poll()
  } catch (e) {
    error.value = errorText(e)
  }
}

const result = computed(() => (job.value ? JSON.stringify(job.value.result, null, 2) : ''))
</script>

<template>
  <section>
    <p><RouterLink to="/admin/jobs">← {{ t('admin.job.back') }}</RouterLink></p>
    <h1>{{ t('admin.job.heading', { id }) }}</h1>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <template v-if="job">
      <div class="row meta">
        <strong>{{ kindText(job.kind, 'title', job.title) }}</strong>
        <JobStatus :status="job.status" />
        <span class="mono muted">{{ job.requested_by ?? t('admin.jobs.scheduler') }} · {{ dateTime(job.created_at) }}</span>
        <span class="mono muted">{{ duration(job.started_at, job.finished_at) }}</span>
        <button v-if="active && session.can('curator') && !job.cancel_requested" class="btn btn-small" type="button" @click="cancel">
          {{ t('admin.jobs.cancel') }}
        </button>
      </div>
      <p v-if="Object.keys(job.params).length" class="mono muted">{{ t('admin.job.params') }}: {{ params(job.params) }}</p>
      <p v-if="job.cancel_requested && active" class="note">{{ t('admin.job.cancelRequested') }}</p>
      <p v-if="job.error" class="alert">{{ t('admin.job.error') }}: {{ job.error }}</p>

      <h2>{{ t('admin.job.log') }} <span class="muted mono">· {{ t('admin.job.lines', { n: job.log_lines }) }}<template v-if="active"> · {{ t('admin.job.follow') }}</template></span></h2>
      <pre ref="logEl" class="log" aria-live="off">{{ lines.length ? lines.join('\n') : t('admin.job.noLog') }}</pre>

      <template v-if="!active && Object.keys(job.result).length">
        <h2>{{ t('admin.job.result') }}</h2>
        <pre class="log">{{ result }}</pre>
      </template>
    </template>
    <p v-else-if="!error" class="muted">{{ t('admin.common.loading') }}</p>
  </section>
</template>

<style scoped>
.meta {
  margin-block-end: 0.5rem;
}
</style>
