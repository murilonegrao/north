import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'
import { mockApi } from './mock/vite-plugin.ts'

// Dev mode: the API runs with `uv run uvicorn` on port 8000 and Vite proxies /api to it.
// `npm run dev:mock` (mode "mock") serves /api from fictitious fixtures instead.
const apiTarget = process.env.NORTH_API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig(({ mode }) => ({
  plugins: [vue(), ...(mode === 'mock' ? [mockApi()] : [])],
  define: {
    __VUE_I18N_FULL_INSTALL__: true,
    __VUE_I18N_LEGACY_API__: false,
    __INTLIFY_PROD_DEVTOOLS__: false,
  },
  server: {
    port: 5173,
    proxy: mode === 'mock' ? undefined : { '/api': apiTarget },
  },
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
  },
}))
