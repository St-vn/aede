import { transcribeViaWebSpeech } from './WebSpeechProvider'
import { API_BASE } from '@/lib/api'

export async function transcribe(audio: Blob, model: string, language?: string): Promise<string> {
  try {
    const form = new FormData()
    form.append('audio', audio, 'clip.webm')
    form.append('model', model)
    if (language) form.append('language', language)
    // API_BASE targets the Python backend (:8000), not the Next dev server.
    // No trailing slash — the backend route is /api/voice/transcribe exactly.
    const resp = await fetch(`${API_BASE}/api/voice/transcribe`, { method: 'POST', body: form })
    const data = await resp.json()
    if (data.text) return data.text
    if (data.fallback === 'webspeech') return await transcribeViaWebSpeech(language)
    return ''
  } catch {
    return await transcribeViaWebSpeech(language)
  }
}
