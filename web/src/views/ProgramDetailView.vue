<script setup lang="ts">
// FR-17: every value with its status, source and date; what is not collected yet is listed,
// never hidden (BR-02: unknown is not negative).
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ApiError, getProgram } from '../api/client'
import type { ProgramDetail } from '../api/types'
import CompletionsText from '../components/CompletionsText.vue'
import StatusBadge from '../components/StatusBadge.vue'
import StatusLegend from '../components/StatusLegend.vue'
import VerifiedField from '../components/VerifiedField.vue'
import { formatDate, formatMoney, formatNumber, keyOf } from '../format'
import { stemKey, useLocalePrefix } from '../programs'

const { t, te, locale } = useI18n()
const route = useRoute()
const prefix = useLocalePrefix()

type Load = { state: 'loading' } | { state: 'not_found' } | { state: 'error' } | { state: 'ok'; data: ProgramDetail }
const load = ref<Load>({ state: 'loading' })
let controller: AbortController | undefined

const id = computed(() => String(route.params.id ?? ''))

async function fetchProgram() {
  controller?.abort()
  controller = new AbortController()
  const signal = controller.signal
  load.value = { state: 'loading' }
  try {
    const data = await getProgram(id.value, signal)
    if (!signal.aborted) load.value = { state: 'ok', data }
  } catch (error) {
    if (signal.aborted) return
    load.value = error instanceof ApiError && error.status === 404 ? { state: 'not_found' } : { state: 'error' }
  }
}

watch(id, fetchProgram, { immediate: true })
onBeforeUnmount(() => controller?.abort())

const program = computed(() => (load.value.state === 'ok' ? load.value.data : null))

// NFR-15: each program page has its own title and description.
watch([program, locale], ([p]) => {
  if (!p) return
  document.title = t('detail.pageTitle', { title: p.title, institution: p.institution.name })
  document
    .querySelector('meta[name="description"]')
    ?.setAttribute('content', t('detail.pageDescription', { title: p.title, institution: p.institution.name, city: p.campus.city }))
})

const num = (n: number) => formatNumber(n, locale.value)
const date = (value: string) => formatDate(value, locale.value)

function notCollectedLabel(field: string): string {
  const key = `detail.notCollectedFields.${keyOf(field)}`
  return te(key) ? t(key) : field
}
function sourceName(source: string): string {
  const key = `detail.sourceNames.${keyOf(source)}`
  return te(key) ? t(key) : source
}
function noteText(code: string): string {
  const key = `detail.notes.${keyOf(code)}`
  return te(key) ? t(key) : code
}
function controlLabel(control: string): string {
  const key = `program.control.${control}`
  return te(key) ? t(key) : control
}
</script>

<template>
  <p class="back">
    <RouterLink :to="`/${prefix}/programs`">{{ t('detail.back') }}</RouterLink>
  </p>

  <p v-if="load.state === 'loading'" class="state-message" aria-live="polite">{{ t('detail.loading') }}</p>

  <div v-else-if="load.state === 'not_found'" class="state-message card" role="alert">
    <h1>{{ t('detail.notFound.title') }}</h1>
    <p>{{ t('detail.notFound.body') }}</p>
  </div>

  <div v-else-if="load.state === 'error'" class="state-message card" role="alert">
    <p>{{ t('detail.error') }}</p>
    <button type="button" class="button-quiet" @click="fetchProgram">{{ t('programs.retry') }}</button>
  </div>

  <article v-else-if="program" aria-labelledby="program-title">
    <header class="program-header">
      <p class="eyebrow">{{ program.degree }} · <code>CIP {{ program.cip.code }}</code></p>
      <h1 id="program-title">{{ program.title }}</h1>
      <p class="where">{{ program.institution.name }} · {{ program.campus.city }}, {{ program.campus.state }}</p>
      <p v-if="program.title_source === 'cip_title'" class="hint">{{ t('program.titleFromCip') }}</p>
      <p v-if="program.flags.includes('no_stem_opt_extension')" class="flag">
        <strong>{{ t('program.flags.no_stem_opt_extension.title') }}</strong>
        {{ t('program.flags.no_stem_opt_extension.body') }}
      </p>
    </header>

    <StatusLegend class="legend-block" />

    <section aria-labelledby="verified-heading" class="card section">
      <h2 id="verified-heading">{{ t('detail.sections.verified') }}</h2>
      <dl>
        <VerifiedField
          :label="t('program.stem')"
          :status="program.stem_opt.status"
          :source-url="program.stem_opt.source_url"
          :verified-at="program.stem_opt.verified_at"
          :evidence="program.stem_opt.evidence"
        >
          {{ t(stemKey(program.stem_opt)) }}
          <template #note>
            <p v-if="program.stem_opt.value?.rule_version" class="note">
              {{ t('detail.values.stemRule', { version: program.stem_opt.value.rule_version }) }}
            </p>
            <p v-if="program.stem_opt.value?.claim_mismatch" class="note">{{ t('detail.values.claimMismatch') }}</p>
          </template>
        </VerifiedField>

        <VerifiedField
          :label="t('detail.fields.sevp')"
          :status="program.campus.intl_authorization.status"
          :source-url="program.campus.intl_authorization.source_url"
          :verified-at="program.campus.intl_authorization.verified_at"
          :evidence="program.campus.intl_authorization.evidence"
        >
          <template v-if="program.campus.intl_authorization.value">
            {{
              program.campus.intl_authorization.value.authorized
                ? t('detail.values.sevpAuthorized')
                : t('detail.values.sevpNotAuthorized')
            }}
          </template>
          <template v-else-if="program.campus.intl_authorization.status === 'confirmed_negative'">
            {{ t('detail.values.sevpNotAuthorized') }}
          </template>
          <span v-else class="muted">{{ t('detail.values.unknown') }}</span>
        </VerifiedField>

        <VerifiedField
          :label="t('detail.fields.accreditation')"
          :status="program.institution.accreditation.status"
          :source-url="program.institution.accreditation.source_url"
          :verified-at="program.institution.accreditation.verified_at"
          :evidence="program.institution.accreditation.evidence"
        >
          <template v-if="program.institution.accreditation.value">
            {{ program.institution.accreditation.value.accreditor }}
            <span class="muted">
              ({{
                program.institution.accreditation.value.institutional
                  ? t('detail.values.institutional')
                  : t('detail.values.programmatic')
              }})
            </span>
          </template>
          <template v-else-if="program.institution.accreditation.status === 'confirmed_negative'">
            {{ t('detail.values.notAccredited') }}
          </template>
          <span v-else class="muted">{{ t('detail.values.unknown') }}</span>
        </VerifiedField>

        <VerifiedField
          :label="t('detail.fields.tuition')"
          :status="program.graduate_tuition_nonresident.status"
          :source-url="program.graduate_tuition_nonresident.source_url"
          :verified-at="program.graduate_tuition_nonresident.verified_at"
          :evidence="program.graduate_tuition_nonresident.evidence"
        >
          <template v-if="program.graduate_tuition_nonresident.value">
            {{ formatMoney(program.graduate_tuition_nonresident.value, locale) }}
          </template>
          <span v-else class="muted">{{ t('detail.values.unknown') }}</span>
          <template v-if="program.graduate_tuition_nonresident.note_code" #note>
            <p class="note tuition-note" data-test="tuition-note">
              {{ noteText(program.graduate_tuition_nonresident.note_code) }}
            </p>
          </template>
        </VerifiedField>

        <VerifiedField
          :label="t('program.completions')"
          :status="program.completions.status"
          :source-url="program.completions.source_url"
          :verified-at="program.completions.verified_at"
          :evidence="program.completions.evidence"
        >
          <CompletionsText :completions="program.completions" />
        </VerifiedField>

        <VerifiedField
          :label="t('detail.fields.carnegie')"
          :status="program.institution.carnegie_classification.status"
          :source-url="program.institution.carnegie_classification.source_url"
          :verified-at="program.institution.carnegie_classification.verified_at"
        >
          <template v-if="program.institution.carnegie_classification.value">
            {{ program.institution.carnegie_classification.value }}
          </template>
          <span v-else class="muted">{{ t('detail.values.unknown') }}</span>
        </VerifiedField>
      </dl>
    </section>

    <section aria-labelledby="missing-heading" class="card section not-collected" data-test="not-collected">
      <h2 id="missing-heading">
        <StatusBadge status="unknown" />
        {{ t('detail.sections.notCollected') }}
      </h2>
      <p class="section-intro">{{ t('detail.notCollectedIntro') }}</p>
      <ul>
        <li v-for="field in program.not_yet_collected" :key="field">{{ notCollectedLabel(field) }}</li>
      </ul>
    </section>

    <section aria-labelledby="facts-heading" class="card section">
      <h2 id="facts-heading">{{ t('detail.sections.facts') }}</h2>
      <dl class="facts">
        <div>
          <dt>{{ t('detail.fields.cip') }}</dt>
          <dd><code>{{ program.cip.code }}</code> {{ program.cip.title }}</dd>
        </div>
        <div v-if="program.cip.isced_f">
          <dt>{{ t('detail.fields.isced') }}</dt>
          <dd><code>{{ program.cip.isced_f }}</code></dd>
        </div>
        <div>
          <dt>{{ t('detail.fields.degree') }}</dt>
          <dd>{{ program.degree }}</dd>
        </div>
        <div>
          <dt>{{ t('detail.fields.institution') }}</dt>
          <dd>
            {{ program.institution.name }} <span class="muted">({{ controlLabel(program.institution.control) }})</span>
          </dd>
        </div>
        <div>
          <dt>{{ t('detail.fields.campus') }}</dt>
          <dd>
            {{ program.campus.city }}, {{ program.campus.state }}
            <span v-if="program.campus.locality" class="muted">· {{ program.campus.locality.name }}</span>
          </dd>
        </div>
        <div v-if="program.institution.website">
          <dt>{{ t('detail.fields.website') }}</dt>
          <dd>
            <a :href="program.institution.website" target="_blank" rel="noopener noreferrer">
              {{ program.institution.website }}<span class="visually-hidden"> ({{ t('detail.meta.newTab') }})</span>
            </a>
          </dd>
        </div>
        <div>
          <dt>{{ t('detail.fields.identifiers') }}</dt>
          <dd>
            <span v-for="(value, key) in program.institution.identifiers" :key="key" class="identifier">
              {{ String(key).toUpperCase() }} <code>{{ value }}</code>
            </span>
          </dd>
        </div>
      </dl>
    </section>

    <section aria-labelledby="sources-heading" class="card section">
      <h2 id="sources-heading">{{ t('detail.sections.sources') }}</h2>
      <p class="section-intro">{{ t('detail.sourcesIntro') }}</p>
      <ul class="sources">
        <li v-for="source in program.sources" :key="`${source.source}-${source.file_version}`">
          <span class="source-name">{{ sourceName(source.source) }}</span>
          <span class="muted">
            {{ t('detail.sourceFile', { version: source.file_version, date: date(source.uploaded_at), rows: num(source.rows) }) }}
          </span>
          <code class="sha" :title="source.sha256">SHA-256 {{ source.sha256.slice(0, 12) }}…</code>
        </li>
      </ul>
    </section>
  </article>
</template>

<style scoped>
.back {
  margin-block: 0 1rem;
  font-family: var(--font-mono);
  font-size: 0.875rem;
}
.program-header {
  margin-block-end: 1.25rem;
}
.program-header code {
  font-size: inherit;
}
h1 {
  margin-block: 0.25rem 0.375rem;
  font-size: clamp(1.5rem, 5vw, 2.125rem);
  overflow-wrap: anywhere;
}
.where {
  margin-block: 0;
  color: var(--text-muted);
}
.hint {
  margin-block: 0.5rem 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.flag {
  margin-block: 0.75rem 0;
  padding-inline-start: 0.75rem;
  border-inline-start: 2px solid var(--text-muted);
  font-size: 0.9375rem;
}
.legend-block {
  margin-block-end: 1.25rem;
}
.section {
  margin-block-end: 1.25rem;
}
h2 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-block: 0 0.5rem;
  font-size: 1rem;
}
dl {
  margin: 0;
}
.note {
  margin-block: 0.25rem 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.tuition-note {
  color: var(--text);
}
.muted {
  color: var(--text-muted);
}
.section-intro {
  margin-block: 0 0.75rem;
  font-size: 0.9375rem;
  color: var(--text-muted);
}
.not-collected {
  border-style: dotted;
}
.not-collected ul {
  margin: 0;
  padding-inline-start: 1.25rem;
}
.not-collected li {
  padding-block: 0.125rem;
}
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
  gap: 0.75rem 1.5rem;
}
.facts dt {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}
.facts dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.identifier {
  margin-inline-end: 1rem;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
}
.sources {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}
.sources li {
  display: flex;
  flex-wrap: wrap;
  gap: 0.125rem 0.75rem;
  font-size: 0.875rem;
}
.source-name {
  font-weight: 500;
}
.sha {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.state-message {
  color: var(--text-muted);
}
.button-quiet {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding-block: 0.375rem;
  padding-inline: 0.75rem;
  cursor: pointer;
}
</style>
