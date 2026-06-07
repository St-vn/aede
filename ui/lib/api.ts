export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export const WS_BASE = API_BASE.replace(/^http/, 'ws')

export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const cleanPath = path.startsWith('/api') ? path.slice(4) : path
  const res = await fetch(`${API_BASE}${cleanPath}`, init)
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json() as Promise<T>
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch(`/sessions/${sessionId}`, { method: 'DELETE' })
}
