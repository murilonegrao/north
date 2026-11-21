import { ref } from 'vue'
import { writeStored } from './storage'

export type Theme = 'dark' | 'light'

const STORAGE_KEY = 'north.theme'

// index.html sets data-theme before first paint; this mirrors it.
export const theme = ref<Theme>(
  document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark',
)

export function toggleTheme(): void {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', theme.value)
  writeStored(STORAGE_KEY, theme.value)
}
