---
type: internal-doc
tags: [docs-internal, web-ui]
date_updated: 2026-06-10
---

# REST API Contract

Base URL: `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_BASE_URL`)

## Sessions

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/sessions` | — | `Session[]` |
| POST | `/api/sessions` | `{model, parent_id?, project_dir?}` | `Session` |
| GET | `/api/sessions/{id}` | — | `Session` |
| PATCH | `/api/sessions/{id}` | `{title?, project_dir?}` | `Session` |
| DELETE | `/api/sessions/{id}` | — | `{status}` |
| GET | `/api/sessions/{id}/messages` | — | `Message[]` (inherits parent messages) |

## Projects

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/projects` | — | `Project[]` |
| POST | `/api/projects` | `{project_dir \| path}` | `Project` (idempotent) |
| DELETE | `/api/projects/{id}` | — | `{status}` |
| POST | `/api/projects/{id}/delete-folder` | — | `{status}` |
| POST | `/api/projects/{id}/remove-git` | — | `{status}` |

## Config

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/config` | — | `AedeConfig` (serialized dict) |
| GET | `/api/config/sources` | — | `{key: source}` |
| PUT | `/api/config` | `{key, value, scope, project_dir?}` | `{status}` |
| POST | `/api/config/open` | `{scope?, project_dir?}` | `{status}` |

## MCP Servers

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/mcp/servers` | — | `{name: McpServerInfo}` (with real status) |
| POST | `/api/mcp/servers` | `{name, command, args?, env?, url?, trusted?, enabled?, disabled_tools?}` | `{status, name}` |
| PUT | `/api/mcp/servers/{name}` | `{enabled?, disabled_tools?}` | `{status, name}` |
| DELETE | `/api/mcp/servers/{name}` | — | `{status, name}` |
| POST | `/api/mcp/servers/restart` | — | `{status, servers[]}` |

## Agents & Skills

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/agents` | — | `AgentInfo[]` |
| POST | `/api/agents` | `{name, ...agent fields}` | `{status, name}` |
| PUT | `/api/agents/{name}` | `{...agent fields, scope?, project_dir?}` | `{status, name}` |
| DELETE | `/api/agents/{name}` | `?scope=&project_dir=` | `{status}` |
| POST | `/api/agents/upload` | `file: UploadFile` (.md/.agent) | `{status, name}` |
| POST | `/api/agents/{name}/open` | — | `{status}` |
| GET | `/api/skills` | — | `SkillInfo[]` |
| POST | `/api/skills` | `{name, ...skill fields}` | `{status, name}` |
| PUT | `/api/skills/{name}` | `{...skill fields, scope?, project_dir?}` | `{status, name}` |
| DELETE | `/api/skills/{name}` | `?scope=&project_dir=` | `{status}` |
| POST | `/api/skills/upload` | `file: UploadFile` (.md/.skill) | `{status, name}` |
| POST | `/api/skills/{name}/open` | — | `{status}` |

## ACP

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/acp/configs` | — | `{configs: AcpConfig[]}` |
| GET | `/api/acp/status` | — | `{connected, active, sessions[]}` |
| POST | `/api/acp/register` | `{name, command, args?, credentials_ref?}` | `{status, name}` |
| DELETE | `/api/acp/{name}` | — | `{status, name}` |
| POST | `/api/acp/connect` | `{name}` | `{status, name, session_id}` |
| POST | `/api/acp/disconnect` | `{name}` | `{status, name}` |

## Models

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/models` | — | `Model[]` |
| POST | `/api/models` | `{id, label, provider}` | `{status}` |
| DELETE | `/api/models/{id}` | — | `{status}` |
| PUT | `/api/models` | `Model[]` | `{status}` (bulk replace) |
| POST | `/api/models/reset` | — | `{status}` |

## Other

| Method | Path | Params | Returns |
|---|---|---|---|
| GET | `/api/credentials` | — | `Credential[]` (no values) |
| POST | `/api/credentials` | `{name, value, provider?}` | `{status, name, acp_connected}` |
| DELETE | `/api/credentials/{name}` | — | `{status}` |
| GET | `/api/learnings` | — | `Learning[]` |
| POST | `/api/learnings` | `{content, type?, source?, source_session_id?, trusted?}` | `Learning` |
| DELETE | `/api/learnings/{id}` | — | `{status}` |
| GET | `/api/token_usage` | `?session_id=` | `{total_input_tokens, total_output_tokens, total_cached_tokens}` |
| GET | `/health` | — | `{status: "ok"}` |
