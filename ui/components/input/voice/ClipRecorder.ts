// Records a single command clip after wake, auto-stopping on end-of-speech.
// Energy gate uses a built-in AnalyserNode (no VAD dependency, per architecture).
// The pure helpers below are unit-tested; the ClipRecorder class wraps browser
// audio APIs and is verified in-browser (Task 12).

const MIDPOINT = 128

/** Mean absolute deviation of a time-domain frame from the 128 midpoint, below
 *  threshold → silence. >= threshold counts as sound. */
export function isSilent(frame: Uint8Array, threshold: number): boolean {
  if (frame.length === 0) return true
  let sum = 0
  for (const v of frame) sum += Math.abs(v - MIDPOINT)
  return sum / frame.length < threshold
}

/** Stop only once speech has occurred AND enough consecutive silent frames followed.
 *  If speech never occurred, the cost gate (in VoiceController) discards instead. */
export function shouldStopOnSilence(s: { hadSpeech: boolean; silentFrames: number; threshold: number }): boolean {
  return s.hadSpeech && s.silentFrames >= s.threshold
}

export interface ClipRecorderOptions {
  silenceThreshold?: number  // amplitude deviation below which a frame is silent
  silenceFrames?: number     // consecutive silent frames before stop (~50Hz poll)
  maxMs?: number             // hard cap so a stuck recorder can't run forever
  onSpeech?: () => void
  onSilence: (clip: Blob | null) => void  // null when no speech was detected (cost gate)
}

export class ClipRecorder {
  private recorder: MediaRecorder | null = null
  private analyser: AnalyserNode | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private raf = 0
  private hardTimer: ReturnType<typeof setTimeout> | null = null
  private chunks: BlobPart[] = []
  private silentFrames = 0
  hadSpeech = false

  constructor(private stream: MediaStream, private ctx: AudioContext) {}

  start(opts: ClipRecorderOptions): void {
    const threshold = opts.silenceThreshold ?? 5
    const stopAfter = opts.silenceFrames ?? 30
    const maxMs = opts.maxMs ?? 15000

    this.analyser = this.ctx.createAnalyser()
    this.analyser.fftSize = 2048
    this.source = this.ctx.createMediaStreamSource(this.stream)
    this.source.connect(this.analyser)
    const buf = new Uint8Array(this.analyser.fftSize)

    this.recorder = new MediaRecorder(this.stream)
    this.recorder.ondataavailable = (e) => { if (e.data.size > 0) this.chunks.push(e.data) }
    this.recorder.onstop = () => {
      const clip = this.hadSpeech ? new Blob(this.chunks, { type: this.recorder?.mimeType || 'audio/webm' }) : null
      opts.onSilence(clip)
    }
    this.recorder.start()

    this.hardTimer = setTimeout(() => this.stop(), maxMs)

    const tick = () => {
      if (!this.analyser) return
      this.analyser.getByteTimeDomainData(buf)
      if (isSilent(buf, threshold)) {
        this.silentFrames++
      } else {
        if (!this.hadSpeech) { this.hadSpeech = true; opts.onSpeech?.() }
        this.silentFrames = 0
      }
      if (shouldStopOnSilence({ hadSpeech: this.hadSpeech, silentFrames: this.silentFrames, threshold: stopAfter })) {
        this.stop()
        return
      }
      this.raf = requestAnimationFrame(tick)
    }
    this.raf = requestAnimationFrame(tick)
  }

  stop(): void {
    if (this.raf) cancelAnimationFrame(this.raf)
    if (this.hardTimer) clearTimeout(this.hardTimer)
    this.raf = 0
    this.hardTimer = null
    try { this.source?.disconnect() } catch { /* already disconnected */ }
    this.analyser = null
    this.source = null
    if (this.recorder && this.recorder.state !== 'inactive') {
      this.recorder.stop()  // fires onstop → onSilence
    }
  }
}
