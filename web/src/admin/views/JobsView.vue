<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { AdminApiError, errorText, get, post } from '../api'
import JobTable from '../components/JobTable.vue'
import { kindText } from '../format'
import { session } from '../session'
import type { Job, JobKind, JobParam, JobStatus } from '../types'

const { t, te } = useI18n()
const paramHelp = (p: JobParam) => (te(`admin.params.${p.name}`, 'en') ? t(`admin.params.${p.name}`) : p.help || p.name)
const route = useRoute()
const router = useRouter()
const STATUSES: JobStatus[] = ['queued', 'running', 'succeeded', 'attention', 'failed', 'cancelled']

const jobs = ref<Job[]>([])
const kinds = ref<JobKind[]>([])
const loading = ref(true)
const error = ref('')
const status = computed(() => (typeof route.query.status === 'string' ? route.query.status : ''))
const PAGE = 50
const more = ref(false)

async function load(append = false) {
  loading.value = true
  error.value = ''
  try {
    const qs = new URLSearchParams({ limit: String(PAGE) })
    if (status.value) qs.set('status', status.value)
    const last = jobs.value.at(-1)
    if (append && last) qs.set('before', String(last.id))
    const page = await get<Job[]>(`/jobs?${qs}`)
    jobs.value = append ? [...jobs.value, ...page] : page
    more.value = page.length === PAGE
  } catch (e) {
    error.value = errorText(e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await load()
  kinds.value = await get<JobKind[]>('/job-kinds')
})
watch(status, () => load())

// Run form
const chosen = ref('')
const values = reactive<Record<string, string | boolean>>({})
const kind = computed(() => kinds.value.find((k) => k.name === chosen.value))
watch(kind, (k) => {
  for (const key of Object.keys(values)) delete values[key]
  for (const p of k?.params ?? []) values[p.name] = p.default
})
const runError = ref('')
const busy = ref(false)

async function run() {
  if (!kind.value) return
  runError.value = ''
  busy.value = true
  try {
    const job = await post<Job>('/jobs', { kind: kind.value.name, params: { ...values } })
    await router.push(`/admin/jobs/${job.id}`)
  } catch (e) {
    if (e instanceof AdminApiError && e.status === 409) {
      runError.value = t('admin.jobs.alreadyActive', { id: String(e.body.job_id) })
    } else {
      runError.value = errorText(e)
    }
  } finally {
    busy.value = false
  }
}

function setStatus(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  void router.replace({ query: value ? { status: value } : {} })
}
</script>

<template>
  <section>
    <h1>{{ t('admin.jobs.heading') }}</h1>

    <div v-if="session.can('curator') && kinds.length" class="card run">
      <h2 class="run-title">{{ t('admin.jobs.run') }}</h2>
      <form class="stack" @submit.prevent="run">
        <div>
          <label for="job-kind">{{ t('admin.jobs.kind') }}</label>
          <select id="job-kind" v-model="chosen" required>
            <option value="" disabled>—</option>
            <option v-for="k in kinds" :key="k.name" :value="k.name" :disabled="!k.allowed">
              {{ kindText(k.name, 'title', k.title) }}{{ k.allowed ? '' : ` (${t('admin.jobs.notAllowed', { role: k.min_role })})` }}
            </option>
          </select>
        </div>
        <p v-if="kind" class="muted">{{ kindText(kind.name, 'description', kind.description) }}</p>
        <div v-for="p in kind?.params ?? []" :key="p.name">
          <label v-if="p.kind === 'bool'" class="check">
            <input v-model="values[p.name]" type="checkbox" /> {{ paramHelp(p) }}
          </label>
          <template v-else>
            <label :for="`param-${p.name}`">{{ p.name }}</label>
            <input :id="`param-${p.name}`" v-model="values[p.name]" type="text" />
            <span class="muted mono">{{ paramHelp(p) }}</span>
          </template>
        </div>
        <p v-if="runError" class="alert" role="alert">{{ runError }}</p>
        <button class="btn btn-primary" type="submit" :disabled="!kind || busy">{{ t('admin.jobs.start') }}</button>
      </form>
    </div>

    <div class="row filter">
      <label for="job-status" class="inline">{{ t('admin.jobs.filter') }}</label>
      <select id="job-status" class="narrow" :value="status" @change="setStatus">
        <option value="">{{ t('admin.jobs.all') }}</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ t(`admin.status.${s}`) }}</option>
      </select>
    </div>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <JobTable :jobs="jobs" />
    <p v-if="loading" class="muted">{{ t('admin.common.loading') }}</p>
    <button v-else-if="more" class="btn" type="button" @click="load(true)">{{ t('admin.jobs.more') }}</button>
  </section>
</template>

<style scoped>
.run {
  max-inline-size: 36rem;
  margin-block-end: 2rem;
}
.run-title {
  margin-block-start: 0;
}
.filter {
  margin-block-end: 0.75rem;
}
.inline {
  margin: 0;
}
.narrow {
  inline-size: auto;
}
</style>
