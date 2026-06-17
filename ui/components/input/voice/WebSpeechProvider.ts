function getSR() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if (typeof window === 'undefined') return undefined
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition
}

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
    r.onerror = (e: any) => { if (!done) reject(new Error(e.error)) }
    r.onend = () => { if (!done) reject(new Error('no-result')) }
    r.start()
  })
}
