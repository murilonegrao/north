import type { Plugin } from 'vite'
import { handleMockRequest } from './handlers.ts'

/** Serves /api from fictitious fixtures so the UI runs without the backend (`npm run dev:mock`). */
export function mockApi(): Plugin {
  return {
    name: 'north-mock-api',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const result = req.url ? handleMockRequest(req.url) : null
        if (!result) return next()
        res.statusCode = result.status
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(result.body))
      })
    },
  }
}
