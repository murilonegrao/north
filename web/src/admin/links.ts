// Email links carry their token in the URL fragment (#token=…): browsers never send the
// fragment to a server, so it stays out of access logs and Referer headers (record 0007).

export function tokenFromHash(hash: string): string {
  const params = new URLSearchParams(hash.replace(/^#/, ''))
  const token = params.get('token') ?? ''
  return /^[\w-]{10,100}$/.test(token) ? token : ''
}

/** Read the token once and drop it from the address bar and the history entry. */
export function takeToken(): string {
  const token = tokenFromHash(window.location.hash)
  if (window.location.hash) {
    window.history.replaceState(window.history.state, '', window.location.pathname + window.location.search)
  }
  return token
}
