// Admin API client: same-origin cookie session, CSRF header on every state-changing request.
import { session } from './session'

export const ADMIN_API = '/api/admin'

export class AdminApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: unknown,
    readonly body: Record<string, unknown> = {},
  ) {
    super(typeof detail === 'string' ? detail : `HTTP ${status}`)
    this.name = 'AdminApiError'
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT'

export async function call<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (method !== 'GET' && session.csrf) headers['X-CSRF-Token'] = session.csrf
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  let response: Response
  try {
    response = await fetch(`${ADMIN_API}${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new AdminApiError(0, 'network error')
  }
  let data: Record<string, unknown> = {}
  try {
    data = (await response.json()) as Record<string, unknown>
  } catch {
    // An empty or HTML body (proxy error page): keep the status only.
  }
  if (!response.ok) {
    // A session that expired or was revoked sends the browser back to the sign-in page.
    if (response.status === 401 && !path.startsWith('/auth/')) session.expire()
    throw new AdminApiError(response.status, data.detail, data)
  }
  return data as T
}

export const get = <T>(path: string) => call<T>('GET', path)
export const post = <T>(path: string, body?: unknown) => call<T>('POST', path, body ?? {})
export const patch = <T>(path: string, body: unknown) => call<T>('PATCH', path, body)

/** Raw-body upload with progress (fetch has no upload progress). */
export function uploadFile(file: File, onProgress: (pct: number) => void): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', `${ADMIN_API}/uploads?filename=${encodeURIComponent(file.name)}`)
    xhr.setRequestHeader('X-CSRF-Token', session.csrf)
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onerror = () => reject(new AdminApiError(0, 'network error'))
    xhr.onload = () => {
      let data: Record<string, unknown> = {}
      try {
        data = JSON.parse(xhr.responseText) as Record<string, unknown>
      } catch {
        // keep empty
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data)
      else reject(new AdminApiError(xhr.status, data.detail, data))
    }
    xhr.send(file)
  })
}

export function errorText(error: unknown): string {
  if (error instanceof AdminApiError) {
    const d = error.detail
    if (typeof d === 'string') return d
    if (d && typeof d === 'object' && 'message' in d) return String((d as { message: unknown }).message)
    return `HTTP ${error.status}`
  }
  return String(error)
}
