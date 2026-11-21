// Shared helpers for the program screens.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import type { CipFamily, StemOpt } from './api/types'
import { byCode } from './locales'

export const CIP_FAMILY_KEYS: Record<CipFamily, string> = {
  '11': 'f11',
  '30.70': 'f30_70',
  '30.71': 'f30_71',
  '52.12': 'f52_12',
}

/** i18n key for the STEM OPT eligibility sentence. Unknown stays unknown (BR-02). */
export function stemKey(stem: StemOpt): string {
  if (stem.status === 'unknown' || !stem.value) return 'program.stemUnknown'
  return stem.value.eligible ? 'program.stemEligible' : 'program.stemNotEligible'
}

/** URL prefix of the current locale, e.g. `pt-br`. */
export function useLocalePrefix() {
  const { locale } = useI18n()
  const route = useRoute()
  return computed(() => (route.params.lang as string | undefined) ?? byCode(locale.value)?.prefix ?? 'en')
}
