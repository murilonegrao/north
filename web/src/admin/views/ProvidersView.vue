<script setup lang="ts">
// Institutions and their private contacts (record 0009), admin only. The list shows how many
// contacts are stored; the contacts of one institution load only when asked, and the server
// writes each read to the audit log. Nothing here is cached or kept in the browser.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { errorText, get } from '../api'
import { dateTime } from '../format'

interface Provider {
  id: string
  name: string
  subdivision: string | null
  programs: number
  contacts: number
  identifiers: Record<string, string>
}
interface Contact {
  name: string | null
  title: string | null
  email: string | null
  phone: string | null
  source: string
  file_version: string
  seen_at: string
}

const { t } = useI18n()
const country = ref<'IE' | 'US'>('IE')
const providers = ref<Provider[]>([])
const contacts = ref<Record<string, Contact[]>>({})
const error = ref('')

async function load() {
  error.value = ''
  contacts.value = {}
  try {
    providers.value = await get<Provider[]>(`/institutions?country=${country.value}`)
  } catch (e) {
    error.value = errorText(e)
  }
}
async function show(id: string) {
  try {
    const r = await get<{ contacts: Contact[] }>(`/institutions/${encodeURIComponent(id)}/contacts`)
    contacts.value = { ...contacts.value, [id]: r.contacts }
  } catch (e) {
    error.value = errorText(e)
  }
}
function hide(id: string) {
  const { [id]: _gone, ...rest } = contacts.value
  contacts.value = rest
}
onMounted(load)
</script>

<template>
  <section>
    <h1>{{ t('admin.providers.heading') }}</h1>
    <p class="muted">{{ t('admin.providers.help') }}</p>
    <div class="stack-inline">
      <label for="providers-country">{{ t('admin.upload.country') }}</label>
      <select id="providers-country" v-model="country" @change="load">
        <option value="IE">{{ t('admin.providers.countries.IE') }}</option>
        <option value="US">{{ t('admin.upload.countries.US') }}</option>
      </select>
    </div>
    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <p v-if="!providers.length && !error" class="note">{{ t('admin.providers.none') }}</p>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('admin.providers.name') }}</th>
            <th>{{ t('admin.providers.identifiers') }}</th>
            <th class="num">{{ t('admin.providers.programs') }}</th>
            <th>{{ t('admin.providers.contacts') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in providers" :key="p.id">
            <td>{{ p.name }}<div class="mono muted">{{ p.id }}<template v-if="p.subdivision"> · {{ p.subdivision }}</template></div></td>
            <td class="mono muted">
              <span v-for="(v, k) in p.identifiers" :key="k">{{ k }} {{ v }} </span>
            </td>
            <td class="num">{{ p.programs }}</td>
            <td>
              <template v-if="!p.contacts"><span class="muted">{{ t('admin.common.none') }}</span></template>
              <template v-else-if="!contacts[p.id]">
                <button class="btn" type="button" :data-test="`show-${p.id}`" @click="show(p.id)">
                  {{ t('admin.providers.show', { n: p.contacts }) }}
                </button>
              </template>
              <template v-else>
                <ul class="contacts" :data-test="`contacts-${p.id}`">
                  <li v-for="(c, i) in contacts[p.id]" :key="i">
                    <strong v-if="c.name">{{ c.name }}</strong>
                    <span v-if="c.title" class="muted"> · {{ c.title }}</span>
                    <div v-if="c.email" class="mono"><a :href="`mailto:${c.email}`">{{ c.email }}</a></div>
                    <div v-if="c.phone" class="mono">{{ c.phone }}</div>
                    <div class="mono muted">{{ c.source }} {{ c.file_version }} · {{ dateTime(c.seen_at) }}</div>
                  </li>
                </ul>
                <button class="btn" type="button" @click="hide(p.id)">{{ t('admin.providers.hide') }}</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.stack-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-block: 0.75rem;
}
.contacts {
  list-style: none;
  margin: 0 0 0.5rem;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}
</style>
