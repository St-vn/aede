export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export const WS_BASE = API_BASE.replace(/^http/, 'ws')

export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json() as Promise<T>
}

export async function apiUpload<T = unknown>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json() as Promise<T>
}
