type State = 'idle' | 'listening' | 'captured' | 'transcribing' | 'done'
interface Deps { getStream: () => Promise<MediaStream>; transcribe: (b: Blob, model?: string) => Promise<string> }

export class VoiceController {
  state: State = 'idle'
  private stream: MediaStream | null = null
  constructor(private deps: Deps) {}

  async start(): Promise<void> {
    if (this.state !== 'idle') return       // idempotent — single owner (ADR-002)
    this.stream = await this.deps.getStream()
    this.state = 'listening'
  }
  stop(): void {
    this.stream?.getTracks().forEach(t => t.stop())
    this.stream = null
    this.state = 'idle'
  }
}
