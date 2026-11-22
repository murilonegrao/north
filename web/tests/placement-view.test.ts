// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SECTIONS } from '../src/placement/bank'
import { loadResults } from '../src/placement/result'
import PlacementView from '../src/views/PlacementView.vue'
import { makeI18n } from './helpers'

const items = SECTIONS.flatMap((s) => s.items)

async function run(pick: (answer: number) => number) {
  const wrapper = mount(PlacementView, { global: { plugins: [makeI18n()] } })
  await wrapper.get('button.primary').trigger('click')
  for (const item of items) {
    expect(wrapper.get('#question').text()).toBe(item.prompt)
    await wrapper.findAll('input[type="radio"]')[pick(item.answer)]!.setValue()
    await wrapper.get('button.primary').trigger('click')
  }
  return wrapper
}

describe('PlacementView (FR-28, FR-29, BR-19)', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
  })

  it('a perfect run shows C1, the estimate label and official ranges with sources', async () => {
    const wrapper = await run((answer) => answer)
    const text = wrapper.text()
    expect(text).toContain('Estimated level: C1')
    expect(text).toContain('Estimate, not an official score')
    expect(text).toContain('Grammar and vocabulary only')
    expect(text).toContain('IELTS Academic')
    expect(text).toContain('7–8')
    expect(wrapper.findAll('a[href^="https://"]').length).toBeGreaterThan(5)
  })

  it('stores the result in the browser only, and shows the change on a retake', async () => {
    await run((answer) => answer)
    expect(loadResults()).toHaveLength(1)
    expect(loadResults()[0]).toMatchObject({ overall: 'C1', bands: { grammar: 'C1', vocabulary: 'C1' } })
    const second = await run((answer) => (answer + 1) % 4)
    expect(second.text()).toContain('below A2')
    expect(second.text()).toContain('down from C1')
    expect(second.text()).toContain(`Review the ${items.length} questions you missed`)
  })
})
