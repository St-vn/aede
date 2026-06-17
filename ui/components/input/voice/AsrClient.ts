import { transcribeViaWebSpeech } from './WebSpeechProvider'

export async function transcribe(audio: Blob, model: string, language?: string): Promise<string> {
  try {
    const form = new FormData()
    form.append('audio', audio, 'clip.webm')
    form.append('model', model)
    if (language) form.append('language', language)
    const resp = await fetch('/api/voice/transcribe', { method: 'POST', body: form })
    const data = await resp.json()
    if (data.text) return data.text
    if (data.fallback === 'webspeech') return await transcribeViaWebSpeech(language)
    return ''
  } catch {
    return await transcribeViaWebSpeech(language)
  }
}
