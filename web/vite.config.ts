import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// Dev mode: the API runs with `uv run uvicorn` on port 8000 and Vite proxies /api to it.
const apiTarget = process.env.NORTH_API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  define: {
    __VUE_I18N_FULL_INSTALL__: true,
    __VUE_I18N_LEGACY_API__: false,
    __INTLIFY_PROD_DEVTOOLS__: false,
  },
  server: {
    port: 5173,
    proxy: { '/api': apiTarget },
  },
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
  },
})
