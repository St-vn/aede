---
type: doc
tags: [docs, features]
date_updated: 2026-06-16
---

# SOUL.md

`SOUL.md` carries your agent's identity, persona, and (in P0.9) the voice
configuration. It is read at session start; the merged result is available
as `cfg.soul` to the agent and to any subsystem that needs it.

## Location

| Tier | Path | Behavior |
|---|---|---|
| Global | `~/.aede/SOUL.md` | Default identity for all projects. |
| Project | `./SOUL.md` (project root) | Overrides global per frontmatter key; persona body replaces global. |

A project SOUL.md is *not* required. The merge is shallow, per-key on
frontmatter, and replaces the body wholesale (no concatenation).

## Format

```markdown
---
name: Jarvis
phonetic: /ˈdʒɑːvɪs/
wake_word: "hey jarvis"
wake_word_phonetic: /heɪ ˈdʒɑːvɪs/
voice:
  engine: piper
  voice_id: en-GB-Ryan
  rate: 1.0
  pitch: 1.0
aliases: [jarvis, j]
---
British butler. Concise and dry. Always cites a source.
```

The block between the two `---` markers is YAML frontmatter. The text
after the closing `---` is the persona prose — injected into the
system prompt as `## Identity` (unchanged from prior versions).

Plain markdown (no frontmatter) is fully supported: the body is the
persona, all typed fields default to `None`.

## CLI: `/soul`

| Command | Effect |
|---|---|
| `/soul` | Print the effective SoulDef. |
| `/soul global` | Open `~/.aede/SOUL.md` in `$EDITOR` (creates it if absent). |
| `/soul project` | Open `./SOUL.md` in `$EDITOR` (creates it if absent). |
| `/soul <key> <value>` | Set a single frontmatter key on the **project** file. |

Allowed keys: `name`, `phonetic`, `wake_word`, `wake_word_phonetic`,
`voice.engine`, `voice.voice_id`, `voice.rate`, `voice.pitch`, `aliases`.

## Web UI

The settings modal **Soul** tab has a scope selector to switch between **Global** (`~/.aede/SOUL.md`) and **Project** (`./SOUL.md`) files. Each frontmatter field is a labeled input; the persona body is an editable textarea. The Save button writes to the selected scope and refreshes `cfg.soul` so the next CLI `/soul` reflects the change without restart. An "Edit file" button opens the file in your OS default editor.

## Failure modes

| Input | Behavior |
|---|---|
| No global, no project | All fields `None`, persona `""`. No `## Identity` block in prompt. |
| Malformed YAML in frontmatter | One yellow warning, frontmatter dropped, body kept. Session continues. |
| UTF-8 decode error | Caller prints a red error and continues with empty soul. |

Per-process warning dedup: each path warns at most once.

## Python API

```python
from aede.config import load_config
from aede.instructions import load_soul_def, SoulDef, VoiceDef

cfg = load_config(home=home, project_dir=project_dir)
soul: SoulDef = cfg.soul
print(soul.name, soul.wake_word, soul.voice.voice_id)
```

`load_soul_def(home, project_dir, *, console=None)` is the parallel
loader for subsystems that don't have a config (returns a fresh
`SoulDef`, never mutates state).
