# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Architecture details: [ARCHITECTURE.md](ARCHITECTURE.md)
> Implementation plan: [plan.md](plan.md)

---

## Module Purpose

`leulit_ia` is an Odoo 17 Community module that integrates an AI assistant directly into the Odoo web interface. Users type questions in natural language inside Odoo and get answers that cross data from multiple leulit_* modules — without knowing which module holds the data, without Excel exports.

**Non-negotiable principle:** every feature must improve the user's daily work. No AI for AI's sake.

---

## System Architecture

The solution runs entirely in Docker containers. The existing Odoo + PostgreSQL containers are extended with new AI services:

```
[Browser — User in Odoo]
    │ writes in purple chat sidebar (AiChatSidebar OWL component)
    ▼
[helipistas_odoo_17]  ← existing container
    │ POST /ai/chat (JSON-RPC, auth='user')
    ▼
[ai-service]  ← new container (FastAPI)
    │ orchestrates: prompt → MCP tools → LLM → response
    ├─── MCP protocol ──────────────────────────────────────────────
    │                 [helipistas-mcp]  ← new container (FastMCP)
    │                   @tool: get_pilot_hours, get_expired_documents…
    │                   @resource: normativa 16 bravo, manuals
    │                   calls Odoo JSON-RPC + Qdrant
    │
    └─── OpenAI format ─────────────────────────────────────────────
                      [litellm-proxy]  ← new container
                        routes to: Claude API | Ollama | Gemini | any
                                          ↓
                      [ollama]  ← optional container (local LLM)
```

**Provider independence:** `ai-service` always speaks OpenAI-format to `litellm-proxy`.
Changing model = edit one line in `litellm/config.yaml`. No code changes.

---

## Key Design Rules

- **ACL enforcement:** all ORM calls inside MCP tools MUST use the env passed from the authenticated user, so Odoo's record rules are enforced automatically. Never bypass with `sudo()` unless explicitly required.
- **System prompt context:** always include current date, user name, and timezone.
- **Credentials:** API keys stored in `ir.config_parameter` via `res.config.settings`. Never hardcoded.
- **Tool loop limit:** max 5 LLM→tool iterations per request (prevents infinite loops).
- **Provider agnostic:** code must work with Claude API and Ollama without modification. Switching provider = config change only.

---

## Module Structure

```
leulit_ia/
├── CLAUDE.md                   # this file
├── ARCHITECTURE.md             # full architecture reference (keep updated)
├── plan.md                     # implementation plan with phases
├── __manifest__.py
├── __init__.py
├── controllers/
│   ├── __init__.py
│   └── main.py                 # /ai/chat route → proxy to ai-service (Phase 4)
├── models/
│   ├── __init__.py
│   ├── ai_tool.py              # AiToolRegistry (interim, replaced by helipistas-mcp in Phase 3)
│   └── res_config_settings.py  # IA credentials / provider / ai-service URL
├── static/src/
│   └── components/
│       └── AiChatSidebar/
│           ├── AiChatSidebar.js    # OWL component
│           ├── AiChatSidebar.xml   # template
│           └── AiChatSidebar.scss  # styles (primary: #7c3aed purple)
├── views/
│   └── res_config_settings_views.xml
├── security/
│   └── ir.model.access.csv
└── docker/
    ├── docker-compose.yml      # all containers (Odoo + IA services)
    ├── .env.example
    ├── odoo.conf
    ├── litellm/config.yaml     # model routing
    ├── ai-service/             # FastAPI orchestrator
    └── helipistas-mcp/         # FastMCP domain server
```

---

## Implementation Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Odoo module scaffold, `res.config.settings`, OWL sidebar | Implemented (needs testing) |
| 2 | Docker infrastructure: ai-service + helipistas-mcp + litellm + qdrant | Pending |
| 3 | helipistas-mcp with 6 real domain tools + normative RAG | Pending |
| 4 | Simplify Odoo controller to HTTP proxy toward ai-service | Pending |
| 5 | Google Drive / Workspace RAG integration | Planned |
| 6 | Audit log (ai.chat.log), metrics, token optimization | Planned |

---

## High-Value Tools (by user ROI)

| Tool | Odoo models | User query |
|------|------------|------------|
| `get_pilot_hours` | leulit_actividad, hr.attendance | "¿Cuántas horas tiene el piloto X este mes?" |
| `get_expired_documents` | leulit_helipuerto | "¿Qué helipuertos tienen documentación caducada?" |
| `get_pending_maintenance` | leulit_taller, leulit_camo, project.task | "¿Qué mantenimiento está pendiente en la base Y?" |
| `get_training_compliance` | leulit_escuela, survey.user_input, hr.employee | "¿Quién no ha completado la formación obligatoria?" |
| `check_regulation_16bravo` | leulit_actividad + RAG | "¿Están los pilotos cumpliendo la 16 bravo?" |
| `get_schedule` | leulit_planificacion, resource.calendar, hr.leave | "¿Cómo está la planificación de la semana?" |

---

## Development Context

- **Odoo version:** 17 **Community** (never Enterprise)
- **Frontend framework:** OWL (Odoo Web Library), asset bundle `web.assets_backend`
- **Route:** `/ai/chat`, type `json`, auth `user`
- **No local Odoo for testing:** provide instructions for the user to test in their Docker test environment

---

## Odoo Community Constraints

This module targets **Odoo 17 Community exclusively**. Never use:

- `_inherit` of Enterprise models (`sign.request`, `documents.document`, `loyalty.program`, `planning.slot`, etc.)
- `web_enterprise` or `web_studio` asset bundles
- `enterprise` key in `__manifest__.py`
- Studio-generated XML ids (`studio_customization.*`)
- Enterprise-only widgets or views (`cohort`, `gantt` — requires `web_gantt` which is Enterprise in v17)
- `sign` module (Enterprise) — use `survey` for course/form logic
- `documents` module (Enterprise) — use `mail` / `report` for document handling

---

## File Scope Rule

Only read and modify files inside `leulit_ia/`. Do not read sibling modules (`leulit_meteo`, `leulit_helipuerto`, etc.) unless the user explicitly asks for it. If you need to understand a leulit_* model's fields, ask the user or check the model file path directly.
