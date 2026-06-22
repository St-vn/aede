---
type: doc
tags: [docs, features]
date_updated: 2026-06-17
---

# Voice Input

Voice input lets you speak to aede through the web UI. Two modes: push-to-talk (manual mic button) and wake word (continuous background listening).

## Architecture

```
Browser mic → ClipRecorder (energy gate) → AsrClient → POST /api/voice/transcribe
                                                         ↓
                                              asr.build_fallback_chain()
                                                         ↓
                                              Groq → OpenAI → OpenRouter → Google
                                                         ↓ (no keys)
                                              WebSpeechProvider (browser-native)
```

### VoiceController

`ui/components/input/voice/VoiceController.ts` is the central orchestrator. It is the single owner of the microphone — wake engine and clip recorder never run concurrently (sequential handoff).

States: `idle → listening → captured → transcribing → done`

Two paths:

- **Push-to-talk**: `VoiceButton` click → `captureOnce()` → records one clip → transcribes → inserts text at cursor
- **Wake word**: `createWakeWordEngine()` arms → wake detected → engine stops (releases mic) → records one clip → transcribes → `onTranscript` auto-submits → engine re-arms

### ClipRecorder

`ui/components/input/voice/ClipRecorder.ts` records a single audio clip after wake detection or push-to-talk. Uses `MediaRecorder` + `AnalyserNode` for energy-based silence detection (no VAD dependency).

Key behaviors:
- Hard cap: 15 seconds max
- Grace window: 4 seconds after start before cost gate can discard (gives speaker time to begin)
- Silent frame threshold: 90 consecutive silent frames (~1.5s at 60fps) after speech has occurred
- `isSilent()` — mean absolute deviation from midpoint 128
- `shouldStopOnSilence()` — stops only after speech has occurred AND consecutive silence threshold met
- Returns `null` for silent clips (cost gate — no API call made)

### AsrClient

`ui/components/input/voice/AsrClient.ts` POSTs audio as `FormData` to `/api/voice/transcribe`. Falls back to `WebSpeechProvider` if the backend signals `fallback: "webspeech"` or on network error.

### WebSpeechProvider

`ui/components/input/voice/WebSpeechProvider.ts` is the floor-level fallback. Uses the browser's native `SpeechRecognition` API — no network required, no API key needed. Only rejects on `not-allowed` / `service-not-allowed`.

### Wake Word Engine

`ui/components/input/voice/wakeWorklet.ts` wraps the `openwakeword-wasm-browser` library. Lazy-imports the WASM/ONNX runtime so nothing loads until voice is enabled.

Default config: keywords `['hey_jarvis']`, threshold 0.5, cooldown 2000ms, execution providers `['wasm']`.

Model files served from `ui/public/openwakeword/models/`:
- `embedding_model.onnx` (1.3 MB)
- `hey_jarvis_v0.1.onnx` (1.3 MB)
- `melspectrogram.onnx` (1.1 MB)
- `silero_vad.onnx` (1.8 MB)

ONNX Runtime WASM files served from `ui/public/onnxruntime/`:
- `ort-wasm-simd-threaded.mjs` + `.wasm` (13 MB)
- `ort-wasm-simd-threaded.jsep.mjs` + `.wasm` (26 MB)

## ASR Backend

### Model Registry

`aede/asr.py` defines `ASR_MODELS` — a registry mapping model names to provider chains and provider-specific model IDs.

| Model | Default Provider | Also Available | Notes |
|-------|-----------------|----------------|-------|
| `whisper-large-v3-turbo` | Groq | OpenAI, OpenRouter | Fastest, cheapest (Groq free tier) |
| `whisper-large-v3` | Groq | OpenAI, OpenRouter | Most accurate |
| `chirp-3` | Google | OpenRouter | Google-native |
| `parakeet-tdt-0.6b-v3` | OpenRouter | — | NVIDIA Parakeet |
| `qwen3-asr-flash` | OpenRouter | — | Alibaba Qwen3 |
| `voxtral-mini-transcribe` | OpenRouter | — | Mistral Voxtral |

### Provider Implementations

| Provider | Protocol | Auth | Endpoint |
|----------|----------|------|----------|
| Groq | OpenAI-compatible SDK | `GROQ_API_KEY` | `api.groq.com/openai/v1` |
| OpenAI | OpenAI SDK | `OPENAI_API_KEY` | `api.openai.com/v1` |
| OpenRouter | Raw HTTP | `OPENROUTER_API_KEY` | `openrouter.ai/api/v1/audio/transcriptions` |
| Google | Raw HTTP | `GOOGLE_API_KEY` | `speech.googleapis.com/v2/speech:recognize` |

### Fallback Chain

`asr.build_fallback_chain(model)` returns an ordered list of `(provider, name, model_id)` tuples for providers that have API keys configured. The server iterates the chain and returns the first successful transcription.

If no API keys are configured, the chain is empty — the server returns `{"fallback": "webspeech"}` and the frontend falls back to browser-native speech recognition.

**Important:** OpenRouter model IDs are namespaced (e.g., `openai/whisper-large-v3-turbo`, `qwen/qwen3-asr-flash-2026-02-10`). Bare IDs cause 400 errors.

## Server Endpoints

### POST /api/voice/transcribe

Accepts `audio` (UploadFile), `model` (default: `whisper-large-v3-turbo`), `language` (optional).

Returns:
- `{"text": "...", "model": "...", "provider": "..."}` on success
- `{"fallback": "webspeech"}` when no API keys are configured
- `{"fallback": "webspeech", "errors": [...]}` when all providers fail

### POST /api/voice/trigger

Logs a wake-word trigger event to the session trace. Accepts `session_id` (required), `wake_word` (required), `source` (`"browser"` or `"ios_shortcut"`, default: `"browser"`). Fail-soft — never returns error on trace write failure.

## Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `voice_input_enabled` | bool | `false` | Enable push-to-talk mic button |
| `voice_wake_word_enabled` | bool | `false` | Enable continuous wake word listening |
| `voice_asr_model` | string | `whisper-large-v3-turbo` | ASR model for transcription |
| `voice_wake_model` | string | `hey_jarvis` | Wake word model to detect |

Configured in the **Soul** tab of the settings modal. The settings UI provides:
- ASR model picker (ordered cheapest first with per-model pricing)
- Wake word model picker ("Hey Jarvis", "Alexa", "Hey Mycroft", "Hey Rhasspy")
- API key inputs for Groq, OpenAI, Google AI, OpenRouter (stored in credential vault)
- Toggle switches for push-to-talk and wake word modes

### SOUL.md Voice Fields

```yaml
---
wake_word: "hey jarvis"
wake_word_phonetic: /heɪ ˈdʒɑːvɪs/
voice:
  engine: piper
  voice_id: en-GB-Ryan
  rate: 1.0
  pitch: 1.0
---
```

### Environment Variables (ASR API Keys)

| Variable | Provider | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Groq | Whisper models (free tier available) |
| `OPENAI_API_KEY` | OpenAI | Whisper models |
| `OPENROUTER_API_KEY` | OpenRouter | Multiple models (Parakeet, Qwen3, Voxtral, etc.) |
| `GOOGLE_API_KEY` | Google | Chirp 3 |

Keys can be set via environment variables or stored in the credential vault (`~/.aede/credentials.json`) through the settings UI or `/setkey`.

## UI Components

| Component | File | Role |
|-----------|------|------|
| `VoiceButton` | `voice/VoiceButton.tsx` | Mic icon button, handles push-to-talk UX |
| `VoiceController` | `voice/VoiceController.ts` | Central state machine, mic owner |
| `ClipRecorder` | `voice/ClipRecorder.ts` | Audio recording with energy-based silence detection |
| `AsrClient` | `voice/AsrClient.ts` | HTTP client for `/api/voice/transcribe` |
| `WebSpeechProvider` | `voice/WebSpeechProvider.ts` | Browser-native fallback |
| `wakeWorklet` | `voice/wakeWorklet.ts` | openWakeWord WASM adapter |
| `PermissionGate` | `voice/PermissionGate.tsx` | Microphone permission warning banner |
| `ErrorDisplay` | `voice/ErrorDisplay.tsx` | Web Speech API error code mapping |
| `useSoulFetch` | `voice/useSoulFetch.ts` | Hook fetching agent soul data |
| `openwakeword-wasm-browser.d.ts` | `voice/openwakeword-wasm-browser.d.ts` | Type declarations for wake word lib |

## Testing

| Test File | Coverage |
|-----------|----------|
| `tests/test_asr.py` | ASR providers, model registry, fallback chain |
| `tests/test_voice_transcribe.py` | POST /api/voice/transcribe endpoint |
| `tests/test_voice_trigger.py` | POST /api/voice/trigger endpoint |
| `ui/__tests__/input/AsrClient.test.ts` | AsrClient HTTP + fallback |
| `ui/__tests__/input/ClipRecorder.test.ts` | ClipRecorder silence detection |
| `ui/__tests__/input/VoiceButton.test.tsx` | VoiceButton state rendering |
| `ui/__tests__/input/WebSpeechProvider.test.ts` | WebSpeechProvider transcription |
