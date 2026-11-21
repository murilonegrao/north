// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { VERIFICATION_STATUSES, type VerificationStatus } from '../src/api/types'
import StatusBadge from '../src/components/StatusBadge.vue'
import StatusLegend from '../src/components/StatusLegend.vue'
import { makeI18n } from './helpers'

const expected: Record<VerificationStatus, { short: string; glyph: string; aria: string }> = {
  confirmed_official: { short: 'Official', glyph: '✓', aria: 'confirmed by an official source' },
  reported_by_program: { short: 'Program site', glyph: '◇', aria: 'reported by the program' },
  extracted_unverified: { short: 'Unverified', glyph: '~', aria: 'extracted, not yet verified' },
  unknown: { short: 'Unknown', glyph: '?', aria: 'unknown' },
  confirmed_negative: { short: 'No', glyph: '✕', aria: 'officially confirmed as no' },
}

describe('StatusBadge', () => {
  it.each(VERIFICATION_STATUSES.map((s) => [s]))('renders the label, glyph and accessible text for %s', (status) => {
    const wrapper = mount(StatusBadge, { props: { status }, global: { plugins: [makeI18n()] } })
    const want = expected[status]
    expect(wrapper.find('.glyph').text()).toBe(want.glyph)
    expect(wrapper.text()).toContain(want.short)
    expect(wrapper.find('.visually-hidden').text()).toBe(`Verification status: ${want.aria}`)
    expect(wrapper.attributes('title')).toBeTruthy()
    expect(wrapper.classes()).toContain(`badge--${status}`)
  })

  it('never renders unknown like a negative (NFR-05)', () => {
    const i18n = makeI18n()
    const unknown = mount(StatusBadge, { props: { status: 'unknown' }, global: { plugins: [i18n] } })
    const negative = mount(StatusBadge, { props: { status: 'confirmed_negative' }, global: { plugins: [i18n] } })
    expect(unknown.text()).not.toEqual(negative.text())
    expect(unknown.find('.glyph').text()).not.toEqual(negative.find('.glyph').text())
  })

  it('legend explains all five statuses', () => {
    const wrapper = mount(StatusLegend, { global: { plugins: [makeI18n()] } })
    expect(wrapper.findAll('li')).toHaveLength(5)
    expect(wrapper.text()).toContain('Unknown does not mean no.')
  })
})
