<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { errorText, uploadFile } from '../api'

const { t } = useI18n()
// Matches NORTH_UPLOAD_MAX_MIB (the server enforces it; this only saves a pointless upload).
const MAX_MIB = 95
const file = ref<File | null>(null)
const pct = ref<number | null>(null)
const error = ref('')
const jobId = ref<number | null>(null)

function choose(event: Event) {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  error.value = ''
  jobId.value = null
}

async function send() {
  if (!file.value) return
  if (file.value.size > MAX_MIB * 1024 * 1024) {
    error.value = t('admin.upload.tooBig', { mb: MAX_MIB })
    return
  }
  error.value = ''
  pct.value = 0
  try {
    const job = await uploadFile(file.value, (p) => (pct.value = p))
    jobId.value = Number(job.id)
  } catch (e) {
    error.value = t('admin.upload.failed', { detail: errorText(e) })
  } finally {
    pct.value = null
  }
}

const ACCEPTED = [
  'HD2024.zip, C2024_A.zip, IC2024_AY.zip, C2024_A_Dict.zip (IPEDS)',
  'certified-school-list-MM-DD-YY.pdf (SEVP)',
  'stemList2024.pdf (DHS)',
  'DAPIP zip (InstitutionCampus.csv + AccreditationRecords.csv)',
  'FY27_FMRs.xlsx (HUD)',
]
</script>

<template>
  <section>
    <h1>{{ t('admin.upload.heading') }}</h1>
    <p class="muted">{{ t('admin.upload.help') }}</p>
    <h2>{{ t('admin.upload.accepted') }}</h2>
    <ul class="mono accepted">
      <li v-for="a in ACCEPTED" :key="a">{{ a }}</li>
    </ul>
    <form class="stack form-card" @submit.prevent="send">
      <div>
        <label for="upload-file">{{ t('admin.upload.choose') }}</label>
        <input id="upload-file" type="file" accept=".zip,.pdf,.xlsx" @change="choose" />
      </div>
      <p v-if="pct !== null" class="mono" role="status">{{ t('admin.upload.sending', { pct }) }}</p>
      <p v-if="error" class="alert" role="alert">{{ error }}</p>
      <p v-if="jobId" class="note" role="status">
        {{ t('admin.upload.done', { id: jobId }) }}
        <RouterLink :to="`/admin/jobs/${jobId}`">{{ t('admin.upload.follow') }}</RouterLink>
      </p>
      <button class="btn btn-primary" type="submit" :disabled="!file || pct !== null">{{ t('admin.upload.send') }}</button>
    </form>
  </section>
</template>

<style scoped>
.accepted {
  padding-inline-start: 1.25rem;
  margin-block: 0 1.5rem;
}
</style>
