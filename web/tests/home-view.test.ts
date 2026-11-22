// @vitest-environment happy-dom
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import { saveResult } from '../src/placement/result'
import HomeView from '../src/views/HomeView.vue'
import { makeI18n, makeRouter } from './helpers'

async function mountHome() {
  const router = makeRouter()
  await router.push('/en/')
  await router.isReady()
  const wrapper = mount(HomeView, { global: { plugins: [makeI18n(), router] } })
  await flushPromises()
  return wrapper
}

describe('HomeView', () => {
  beforeEach(() => window.localStorage.clear())

  it('shows the path in order, with available steps linked and the rest marked coming soon', async () => {
    const wrapper = await mountHome()
    const steps = wrapper.findAll('.step')
    expect(steps.map((s) => s.get('h3').text())).toEqual(['Your English level', 'An English course in Ireland', 'Degree programs', 'Family and cost'])
    expect(steps.map((s) => s.get('.pill').text())).toEqual(['Available', 'Available', 'Available', 'Coming soon'])
    expect(steps[0]!.get('a').attributes('href')).toBe('/en/placement')
    // E2: the English course step is live and links to the course list.
    expect(steps[1]!.get('a').attributes('href')).toBe('/en/english-courses')
    expect(steps[1]!.get('a').text()).toBe('Browse courses')
    expect(steps[2]!.get('a').attributes('href')).toBe('/en/programs')
    expect(steps[3]!.find('a').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('API status')
  })

  it('shows the last placement result kept in this browser', async () => {
    saveResult({ taken_at: '2026-11-22T12:00:00Z', bank_version: '0.1', bands: { grammar: 'B2', vocabulary: 'B1' }, overall: 'B1' })
    const wrapper = await mountHome()
    expect(wrapper.get('.last').text()).toContain('Your last result: B1')
    expect(wrapper.findAll('.step')[0]!.get('a').text()).toBe('Take it again')
  })
})
