<script setup lang="ts">
// Home: the path in order (English → course → degree → family), each step marked available or
// coming soon. A step goes live by flipping `available`, without redoing the layout.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { loadResults } from '../placement/result'
import { useLocalePrefix } from '../programs'

const { t, locale } = useI18n()
const prefix = useLocalePrefix()

interface Step {
  key: 'english' | 'course' | 'degree' | 'family'
  available: boolean
  to?: string
}

const steps = computed<Step[]>(() => [
  { key: 'english', available: true, to: `/${prefix.value}/placement` },
  { key: 'course', available: true, to: `/${prefix.value}/english-courses` },
  { key: 'degree', available: true, to: `/${prefix.value}/programs` },
  { key: 'family', available: false },
])

// The last placement result, read from this browser only (BR-19).
const last = loadResults().at(-1) ?? null
const lastLevel = last ? (last.overall === 'below_A2' ? t('placement.belowA2') : last.overall) : ''
const lastDate = last ? new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium' }).format(new Date(last.taken_at)) : ''
</script>

<template>
  <section class="intro" aria-labelledby="title">
    <h1 id="title">North</h1>
    <p class="tagline">{{ t('home.tagline') }}</p>
    <p class="description">{{ t('home.description') }}</p>
  </section>

  <section class="path" aria-labelledby="path-title">
    <h2 id="path-title">{{ t('home.pathTitle') }}</h2>
    <ol class="steps">
      <li v-for="(step, i) in steps" :key="step.key" :class="['step', { soon: !step.available }]">
        <div class="step-head">
          <span class="step-number" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <span :class="['pill', step.available ? 'live' : 'later']">
            {{ step.available ? t('home.available') : t('home.soon') }}
          </span>
        </div>
        <h3>{{ t(`home.steps.${step.key}.title`) }}</h3>
        <p>{{ t(`home.steps.${step.key}.text`) }}</p>
        <p v-if="step.key === 'english' && last" class="last">
          {{ t('home.lastResult', { level: lastLevel, date: lastDate }) }}
        </p>
        <RouterLink v-if="step.available && step.to" :to="step.to" class="cta">
          {{ step.key === 'english' && last ? t('home.steps.english.again') : t(`home.steps.${step.key}.cta`) }}
        </RouterLink>
      </li>
    </ol>
  </section>

  <section class="trust" aria-labelledby="trust-title">
    <h2 id="trust-title" class="visually-hidden">{{ t('home.trustTitle') }}</h2>
    <ul>
      <li><strong>{{ t('home.trust.sources.title') }}</strong> {{ t('home.trust.sources.text') }}</li>
      <li><strong>{{ t('home.trust.unknown.title') }}</strong> {{ t('home.trust.unknown.text') }}</li>
      <li><strong>{{ t('home.trust.advice.title') }}</strong> {{ t('home.trust.advice.text') }}</li>
    </ul>
  </section>
</template>

<style scoped>
.intro {
  max-inline-size: var(--measure);
}
h1 {
  margin-block: 0 0.5rem;
  font-size: clamp(2rem, 6vw, 2.75rem);
}
.tagline {
  margin-block: 0 1rem;
  font-family: var(--font-mono);
  font-size: 1rem;
  text-wrap: balance;
}
.description {
  margin-block: 0;
  color: var(--text-muted);
}
.path {
  margin-block-start: 2.5rem;
}
h2 {
  margin-block: 0 1rem;
  font-size: 1.125rem;
}
.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr));
  gap: 1rem;
}
.step {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  min-inline-size: 0;
}
.step-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.step-number {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.pill {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding-block: 0.125rem;
  padding-inline: 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text-muted);
}
.pill.live {
  border-color: var(--accent);
  color: var(--accent-text);
}
h3 {
  margin: 0;
  font-size: 1.0625rem;
  font-family: var(--font-sans);
  font-weight: 600;
}
.step p {
  margin: 0;
  font-size: 0.9375rem;
}
.step.soon h3,
.step.soon p {
  color: var(--text-muted);
}
.last {
  font-family: var(--font-mono);
  font-size: 0.8125rem !important;
}
.cta {
  margin-block-start: auto;
  align-self: flex-start;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 0.9375rem;
  color: var(--charcoal); /* 5.3:1 on ember in both themes */
  background: var(--accent);
  border-radius: var(--radius);
  padding-block: 0.5rem;
  padding-inline: 1rem;
  text-decoration: none;
}
.cta:hover {
  color: var(--charcoal);
  text-decoration: underline;
}
.trust {
  margin-block-start: 2.5rem;
  max-inline-size: var(--measure);
}
.trust ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.75rem;
  border-block-start: 1px solid var(--border);
  padding-block-start: 1.25rem;
}
.trust li {
  font-size: 0.9375rem;
  color: var(--text-muted);
}
.trust strong {
  color: var(--text);
  font-weight: 600;
}
.visually-hidden {
  position: absolute;
  inline-size: 1px;
  block-size: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
</style>
