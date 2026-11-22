import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'
import { parse as parseYaml } from 'yaml'
import { mockApi } from './mock/vite-plugin.ts'

// Dev mode: the API runs with `uv run uvicorn` on port 8000 and Vite proxies /api to it.
// `npm run dev:mock` (mode "mock") serves /api from fictitious fixtures instead.
const apiTarget = process.env.NORTH_API_URL ?? 'http://127.0.0.1:8000'

// The placement item bank is YAML in data/placement/items (record 0008/T21); it is parsed here,
// at build time, so the browser gets plain JSON and no YAML parser.
const yamlModules = {
  name: 'north-yaml',
  transform(code: string, id: string) {
    if (!id.endsWith('.yaml')) return null
    return { code: `export default ${JSON.stringify(parseYaml(code))}`, map: null }
  },
}

export default defineConfig(({ mode }) => ({
  plugins: [vue(), yamlModules, ...(mode === 'mock' ? [mockApi()] : [])],
  define: {
    __VUE_I18N_FULL_INSTALL__: true,
    __VUE_I18N_LEGACY_API__: false,
    __INTLIFY_PROD_DEVTOOLS__: false,
  },
  build: {
    // Fonts are never inlined as data: URIs, so the CSP keeps font-src 'self' (no data:).
    assetsInlineLimit: (file: string) => (/\.(woff2?|ttf|otf)$/.test(file) ? false : undefined),
  },
  server: {
    port: 5173,
    // The item bank and the CEFR tables live in ../data.
    fs: { allow: ['..'] },
    proxy: mode === 'mock' ? undefined : { '/api': apiTarget },
  },
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
  },
}))
