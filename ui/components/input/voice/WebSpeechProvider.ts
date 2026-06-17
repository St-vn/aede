function getSR() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if (typeof window === 'undefined') return undefined
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
}

// Resolves the transcript, or '' when nothing was recognized. Only rejects when
// Web Speech is genuinely unavailable — "no speech heard" is an empty result,
// not an error, so callers never get an unhandled rejection for silence.
export function transcribeViaWebSpeech(lang?: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const SR = getSR()
    if (!SR) return reject(new Error('no-speech-recognition'))
    const r = new SR()
    r.continuous = false; r.interimResults = false
    r.lang = lang ?? (typeof navigator !== 'undefined' ? navigator.language : 'en-US')
    let done = false
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onresult = (e: any) => { done = true; resolve(e.results[0][0].transcript) }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onerror = (e: any) => {
      if (done) return
      done = true
      // permission/unavailable are real errors; no-speech/aborted are just silence.
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') reject(new Error(e.error))
      else resolve('')
    }
    r.onend = () => { if (!done) { done = true; resolve('') } }
    r.start()
  })
}
