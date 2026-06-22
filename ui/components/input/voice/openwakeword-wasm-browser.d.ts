// Ambient types for openwakeword-wasm-browser v0.1.1 (ships no types; raw src).
// Surface verified against the actual package tarball (src/WakeWordEngine.js).
declare module 'openwakeword-wasm-browser' {
  export interface WakeWordEngineOptions {
    keywords?: string[]
    baseAssetUrl?: string
    detectionThreshold?: number
    cooldownMs?: number
    executionProviders?: string[]
    ortWasmPath?: string
    sampleRate?: number
    gain?: number
    debug?: boolean
  }
  export class WakeWordEngine {
    constructor(opts?: WakeWordEngineOptions)
    load(): Promise<void>
    start(opts?: { deviceId?: string; gain?: number }): Promise<void>
    stop(): Promise<void>
    on(event: string, handler: (payload: unknown) => void): () => void
    off(event: string, handler: (...args: unknown[]) => void): void
  }
  export const MODEL_FILE_MAP: Record<string, string>
  export default WakeWordEngine
}
