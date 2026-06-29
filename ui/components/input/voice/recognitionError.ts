'use client'

const errorMessages: Record<string, string> = {
  'audio-capture': 'Microphone unavailable. Check your mic connection.',
  'network': 'Voice input requires an internet connection.',
  'not-allowed': 'Microphone access blocked. Open site settings to re-enable.',
  'service-not-allowed': 'Microphone access blocked. Open site settings to re-enable.',
  'language-not-supported': 'Language not supported. Falling back to en-US.',
  'phrases-not-supported': 'Wake word biasing unavailable. Falling back to text match.',
}

const errorTypes: Record<string, 'error' | 'warning' | 'info'> = {
  'audio-capture': 'error',
  'network': 'warning',
  'not-allowed': 'error',
  'service-not-allowed': 'error',
  'language-not-supported': 'info',
  'phrases-not-supported': 'info',
}

export function handleRecognitionError(code: string): { message: string; type: string } | null {
  if (code === 'no-speech' || code === 'aborted') return null
  return {
    message: errorMessages[code] ?? 'Voice input error.',
    type: errorTypes[code] ?? 'error',
  }
}
