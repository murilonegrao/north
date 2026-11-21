<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocalePrefix } from '../programs'

const { t } = useI18n()
const prefix = useLocalePrefix()

type Health = { state: 'checking' } | { state: 'ok'; version: string } | { state: 'down' }
const health = ref<Health>({ state: 'checking' })

onMounted(async () => {
  try {
    const response = await fetch('/api/health', { headers: { Accept: 'application/json' } })
    if (!response.ok) throw new Error(String(response.status))
    const body = (await response.json()) as { status?: string; version?: string }
    health.value =
      body.status === 'ok' ? { state: 'ok', version: body.version ?? '?' } : { state: 'down' }
  } catch {
    health.value = { state: 'down' }
  }
})
</script>

<template>
  <section class="hero" aria-labelledby="title">
    <p class="eyebrow">{{ t('home.eyebrow') }}</p>
    <h1 id="title">North</h1>
    <p class="tagline">{{ t('home.tagline') }}</p>
    <p class="description">{{ t('home.description') }}</p>
    <p class="browse">
      <RouterLink :to="`/${prefix}/programs`" class="browse-link">{{ t('home.browse') }}</RouterLink>
      <span class="browse-hint">{{ t('home.browseHint') }}</span>
    </p>
  </section>

  <section class="card status" aria-live="polite">
    <span class="eyebrow">{{ t('status.label') }}</span>
    <span :class="['status-value', health.state]">
      <span class="dot" aria-hidden="true"></span>
      <template v-if="health.state === 'checking'">{{ t('status.checking') }}</template>
      <template v-else-if="health.state === 'ok'">{{ t('status.ok', { version: health.version }) }}</template>
      <template v-else>{{ t('status.down') }}</template>
    </span>
  </section>
</template>

<style scoped>
.hero {
  max-inline-size: var(--measure);
}
h1 {
  margin-block: 0.25rem 0.5rem;
  font-size: clamp(2rem, 6vw, 2.75rem);
}
.tagline {
  margin-block: 0 1.25rem;
  font-family: var(--font-mono);
  font-size: 0.9375rem;
  color: var(--text-muted);
}
.description {
  margin-block: 0;
}
.browse {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
  margin-block: 1.75rem 0;
}
.browse-link {
  display: inline-block;
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--charcoal); /* 5.3:1 on ember in both themes */
  background: var(--accent);
  border-radius: var(--radius);
  padding-block: 0.5rem;
  padding-inline: 1rem;
  text-decoration: none;
}
.browse-link:hover {
  color: var(--charcoal);
  text-decoration: underline;
}
.browse-hint {
  font-size: 0.875rem;
  color: var(--text-muted);
}
.status {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 1rem;
  margin-block-start: 2.5rem;
  max-inline-size: var(--measure);
}
.status-value {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.dot {
  inline-size: 0.5rem;
  block-size: 0.5rem;
  border-radius: 50%;
  border: 1px solid var(--text-muted);
}
.status-value.ok {
  color: var(--text);
}
.status-value.ok .dot {
  background: var(--accent);
  border-color: var(--accent);
}
</style>
