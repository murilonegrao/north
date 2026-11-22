/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

// YAML files are turned into JSON modules at build time (vite.config.ts, plugin north-yaml).
declare module '*.yaml' {
  const data: unknown
  export default data
}
