// Thin adapter over openwakeword-wasm-browser. The engine embeds its own
// AudioWorklet processor and owns its own getUserMedia stream — we do not
// write a worklet file. Lazy-imported so the WASM/ONNX runtime only loads
// when voice is actually enabled.

export interface WakeWordOptions {
  baseAssetUrl?: string        // where the .onnx models are served, default '/openwakeword/models'
  keywords?: string[]          // default ['hey_jarvis']
  detectionThreshold?: number  // default 0.5
  cooldownMs?: number          // default 2000 — prevent double-fire
}

export interface WakeWordHandle {
  load(): Promise<void>
  start(): Promise<void>
  stop(): Promise<void>
  on(event: 'detect', handler: (p: { keyword: string; score: number }) => void): void
  on(event: 'speech-start' | 'speech-end' | 'ready', handler: () => void): void
  on(event: 'error', handler: (e: unknown) => void): void
  off(event: string, handler: (...args: unknown[]) => void): void
}

const DEFAULTS = {
  baseAssetUrl: '/openwakeword/models',
  // Vendored onnxruntime-web wasm binaries (public/onnxruntime/). Without this,
  // ort tries to load its .wasm from a default path that 404s under Next.js.
  ortWasmPath: '/onnxruntime/',
  keywords: ['hey_jarvis'],
  detectionThreshold: 0.5,
  cooldownMs: 2000,
  debug: true,  // logs '[WakeWordEngine] Keyword score {...}' per frame — temporary, for tuning
}

/** Create a wake-word engine. Lazy-imports the package so nothing loads until
 *  voice is enabled. The engine acquires its own mic stream on start(). */
export async function createWakeWordEngine(opts: WakeWordOptions = {}): Promise<WakeWordHandle> {
  const { WakeWordEngine } = await import('openwakeword-wasm-browser')
  return new WakeWordEngine({ ...DEFAULTS, ...opts, executionProviders: ['wasm'] }) as unknown as WakeWordHandle
}
