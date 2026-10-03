/** The signed-in user, as returned by /api/v1/auth/me. */
export interface SessionUser {
  id: number
  email: string
}

/** Read the backend's error body when it has one, else a generic message. */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (
      typeof body === 'object' &&
      body !== null &&
      'detail' in body &&
      typeof body.detail === 'string'
    ) {
      return body.detail
    }
  } catch {
    // A non-JSON body is fine; fall through to the generic message.
  }
  return `Request failed with HTTP ${response.status}`
}

/** Same-origin fetch with cookies attached and JSON headers set. */
async function send(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

/** Return the current user, or null when no session is active. */
export async function fetchSession(): Promise<SessionUser | null> {
  const response = await send('/api/v1/auth/me')
  if (response.status === 401) {
    return null
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return (await response.json()) as SessionUser
}

/** Log in and return the user; throws a readable error when it fails. */
export async function login(email: string, password: string): Promise<SessionUser> {
  const response = await send('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return (await response.json()) as SessionUser
}

/** End the session. */
export async function logout(): Promise<void> {
  const response = await send('/api/v1/auth/logout', { method: 'POST' })
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
}
