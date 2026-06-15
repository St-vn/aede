---
type: doc
tags: [docs, features]
date_updated: 2026-06-14
---

# Voice Input

Voice input lets you speak to aede through the web UI. Two modes:

## Press-to-Talk (VoiceButton)

A microphone button in the input bar. Press to start recording, release to send. Wraps the browser `SpeechRecognition` API with a `recognitionState` reducer for error-resilient capture.

## Wake Word (WakeWordListener)

Continuous listening in the background. When a configured wake word is detected, the agent starts listening for a command. Uses suffix matching + Levenshtein distance (≤ 2) for robust wake word detection.

### Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `voice_input_enabled` | bool | `false` | Enable voice input in the web UI |
| `voice_wake_word_enabled` | bool | `false` | Enable wake word detection |

Configured in the Soul tab of the settings modal, alongside the wake word text and phonetic spelling in `SOUL.md`:

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
