# Arquitectura del Asistente IA — Helipistas ERP

> Documento vivo. Actualizar cuando cambie cualquier decisión arquitectónica.
> Última actualización: 2026-04-16

---

## 1. Visión general

El asistente IA de Helipistas permite a los usuarios consultar información de negocio en lenguaje natural directamente desde la interfaz de Odoo. El sistema cruza datos de múltiples módulos (`leulit_actividad`, `leulit_helipuerto`, `leulit_taller`, etc.) y los combina con documentación normativa para dar respuestas contextualizadas.

**Principio de diseño fundamental:** la arquitectura es independiente del proveedor de LLM. Cambiar de Claude API a un modelo local (Ollama, vLLM) o a cualquier otro proveedor cloud (Gemini, OpenRouter) solo requiere editar un fichero de configuración, sin cambiar código.

---

## 2. Diagrama de contenedores

```
┌─────────────────────────────────────────────────────────────────────┐
│  NAVEGADOR — Usuario en Odoo                                        │
│  Escribe en el chat sidebar (panel morado, esquina derecha)         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP (interno)
                           ▼
┌──────────────────────────────────────────┐
│  helipistas_odoo_17                      │  puerto 8070 → 8069
│  Imagen: wbms/odoo-17.0                  │  EXISTENTE
│                                          │
│  Módulo leulit_ia:                       │
│  - AiChatSidebar (OWL, systray)          │
│  - POST /ai/chat → proxy a ai-service    │
│  - res.config.settings (URL ai-service)  │
└──────────────────┬───────────────────────┘
                   │ HTTP POST /chat
                   │ { prompt, history, user_id }
                   ▼
┌──────────────────────────────────────────┐
│  ai-service                              │  puerto 8001
│  Imagen: custom (FastAPI)                │  NUEVO
│                                          │
│  - Recibe prompt del usuario             │
│  - Construye system prompt               │
│  - Gestiona loop: LLM ↔ MCP tools       │
│  - Máx. 5 iteraciones por request        │
│  - Retorna respuesta en lenguaje natural │
└───────┬──────────────────────────────────┘
        │                    │
        │ OpenAI API format  │ MCP protocol (stdio/SSE)
        ▼                    ▼
┌───────────────┐   ┌────────────────────────────────────────────────┐
│ litellm-proxy │   │  helipistas-mcp                                │  puerto 8002
│ puerto 4000   │   │  Imagen: custom (FastMCP)                      │  NUEVO
│               │   │                                                │
│ Enruta a:     │   │  @tool get_pilot_hours(pilot, period)          │
│ - Claude API  │   │  @tool get_expired_documents(helipuerto)       │
│ - Ollama      │   │  @tool get_pending_maintenance(base)           │
│ - Gemini      │   │  @tool get_training_compliance(employee)       │
│ - cualquier   │   │  @tool check_regulation_16bravo(pilot)         │
│   proveedor   │   │  @tool get_schedule(employee, dates)           │
│               │   │                                                │
│ config.yaml   │   │  @resource normativa://16bravo                 │
│ = 1 línea     │   │  @resource manual://operaciones                │
│   para        │   │  @resource perfiles://formacion                │
│   cambiar     │   │                                                │
│   modelo      │   │  Conecta a:                                    │
└───────┬───────┘   │  - Odoo JSON-RPC (odoo_client.py)             │
        │           │  - Qdrant (rag.py)                             │
        │           └─────────────────┬──────────────────────────────┘
        │                             │
        ▼                             ▼
┌───────────────┐           ┌─────────────────┐
│  ollama       │           │  qdrant          │  puerto 6333
│  puerto 11434 │           │  Vector DB       │  NUEVO
│  OPCIONAL     │           │                  │
│               │           │  Índices:        │
│  Modelos:     │           │  - normativa_16b │
│  qwen2.5:7b   │           │  - manuales      │
│  llama3.2:3b  │           │  - gdrive (f.5)  │
│  mistral:7b   │           └─────────────────┘
└───────────────┘
        │
        ▼
  (cloud providers)
  Claude API
  Gemini API
  OpenRouter
  etc.

┌──────────────────────────────────────────┐
│  helipistas_psql_15                      │  puerto 5432
│  Imagen: postgres:15                     │  EXISTENTE
│  DB: productiu                           │
└──────────────────────────────────────────┘
```

---

## 3. Contenedores

### Existentes (no modificar imagen)

| Contenedor | Imagen | Puerto | Notas |
|---|---|---|---|
| `helipistas_psql_15` | `postgres:15` | 5432 | DB productiu |
| `helipistas_odoo_17` | `wbms/odoo-17.0` | 8070→8069 | `--dev=all` en dev |

### Nuevos (Fase 2+)

| Contenedor | Imagen | Puerto interno | Puerto host |
|---|---|---|---|
| `ai-service` | `./ai-service` (custom) | 8001 | 8001 |
| `helipistas-mcp` | `./helipistas-mcp` (custom) | 8002 | — (interno) |
| `litellm-proxy` | `ghcr.io/berriai/litellm` | 4000 | 4000 |
| `ollama` | `ollama/ollama` | 11434 | 11434 (opcional) |
| `qdrant` | `qdrant/qdrant` | 6333/6334 | 6333 |

---

## 4. Flujo de una consulta

```
1. Usuario escribe: "¿Cuántas horas tiene acumuladas el piloto García este mes?"

2. AiChatSidebar (OWL) → POST /ai/chat { prompt, history }

3. Odoo controller → POST http://ai-service:8001/chat

4. ai-service construye:
   - system_prompt: "Eres el asistente de Helipistas. Fecha: 2026-04-16. Usuario: Admin."
   - tool_definitions: [get_pilot_hours, get_expired_documents, …]
   - messages: [{ role: user, content: "¿Cuántas horas…?" }]

5. ai-service → litellm-proxy → Claude API (o Ollama)
   LLM responde: tool_use { name: "get_pilot_hours", input: { pilot: "García", period: "2026-04" } }

6. ai-service → helipistas-mcp → execute get_pilot_hours
   helipistas-mcp → Odoo JSON-RPC: busca en leulit_actividad con user env del usuario
   Devuelve: { pilot: "García", hours: 42.5, flights: 18, period: "Abril 2026" }

7. ai-service → litellm-proxy → Claude API con resultado del tool
   LLM sintetiza: "El piloto García lleva 42,5 horas acumuladas en abril 2026, distribuidas en 18 vuelos."

8. ai-service → Odoo controller → AiChatSidebar → renderiza en burbuja de chat
```

---

## 5. Independencia de proveedor

El `ai-service` siempre habla **OpenAI API format** hacia `litellm-proxy`. LiteLLM hace la traducción al proveedor real.

### Cambiar de Claude a Ollama

Editar `docker/litellm/config.yaml`:

```yaml
model_list:
  - model_name: helipistas-default
    litellm_params:
      # ANTES:
      # model: claude-3-5-haiku-20241022
      # api_key: ${CLAUDE_API_KEY}
      # DESPUÉS:
      model: ollama/qwen2.5:7b
      api_base: http://ollama:11434
```

```bash
docker compose restart litellm-proxy
```

Ningún otro fichero cambia.

### Proveedores soportados por LiteLLM

| Proveedor | Modelo ejemplo | Uso recomendado |
|---|---|---|
| Anthropic Claude | `claude-3-5-haiku-20241022` | Producción — mejor balance calidad/coste |
| Ollama local | `ollama/qwen2.5:7b` | Desarrollo local / datos sensibles |
| Ollama local | `ollama/llama3.2:3b` | Pruebas rápidas, hardware limitado |
| Google Gemini | `gemini/gemini-1.5-flash` | Alternativa cloud económica |
| OpenRouter | `openrouter/…` | Acceso multi-proveedor con una sola key |

---

## 6. Servidor MCP Helipistas (`helipistas-mcp`)

Implementado con [FastMCP](https://github.com/jlowin/fastmcp). Tres tipos de primitivas:

### @tool — Acceso a datos de Odoo en tiempo real

Todos los tools llaman al ORM de Odoo via JSON-RPC autenticado con las credenciales del usuario actual, garantizando que las ACLs y record rules de Odoo se respetan.

```python
@mcp.tool()
def get_pilot_hours(pilot_name: str, period: str) -> dict:
    """Horas acumuladas de un piloto en un periodo (YYYY-MM)."""
    ...

@mcp.tool()
def get_expired_documents(helipuerto_name: str = None) -> list:
    """Documentos caducados o próximos a caducar en helipuertos."""
    ...

@mcp.tool()
def check_regulation_16bravo(pilot_name: str) -> dict:
    """Verifica cumplimiento normativa 16 bravo (horas vuelo/descanso)."""
    ...
```

### @resource — Documentación normativa para RAG

```python
@mcp.resource("normativa://16bravo")
def get_normativa_16bravo() -> str:
    """Texto completo de la normativa aeronáutica 16 bravo."""
    ...

@mcp.resource("manual://operaciones")
def get_manual_operaciones() -> str:
    """Manual de operaciones interno de Helipistas."""
    ...
```

### @prompt — Consultas frecuentes pre-construidas

```python
@mcp.prompt()
def resumen_diario_base(base: str) -> list:
    """Prompt optimizado para resumen diario de una base operativa."""
    ...
```

---

## 7. RAG (Retrieval-Augmented Generation)

Qdrant almacena embeddings de documentos normativos y manuales. El servidor MCP consulta Qdrant antes de invocar al LLM para enriquecer el contexto.

### Documentos indexados (Fase 3)

- Normativa aeronáutica 16 bravo
- Manual de operaciones interno
- Perfiles de formación por puesto
- Procedimientos de calidad

### Documentos indexados (Fase 5 — Google Drive)

- Toda la documentación corporativa en Google Workspace
- Indexado periódico (cada 6h) via `gdrive-indexer`
- Búsqueda semántica: "¿Qué documentos afecta la actualización de la normativa X?"

---

## 8. Estructura de ficheros Docker

```
docker/
├── docker-compose.yml          # orquestación completa
├── .env                        # variables secretas (no versionar)
├── .env.example                # plantilla pública
├── odoo.conf                   # configuración Odoo (existente)
├── litellm/
│   └── config.yaml             # routing de modelos LLM
├── ai-service/
│   ├── Dockerfile
│   ├── requirements.txt        # fastapi, uvicorn, openai, mcp
│   └── main.py                 # FastAPI: orquesta prompt → MCP → LiteLLM
├── helipistas-mcp/
│   ├── Dockerfile
│   ├── requirements.txt        # fastmcp, httpx, qdrant-client
│   ├── server.py               # FastMCP server principal
│   ├── odoo_client.py          # cliente JSON-RPC para Odoo
│   ├── rag.py                  # consultas semánticas a Qdrant
│   └── documents/              # documentos semilla para RAG
│       ├── normativa_16bravo.md
│       └── manual_operaciones.md
└── gdrive-indexer/             # Fase 5
    ├── Dockerfile
    ├── requirements.txt
    └── indexer.py              # crawl Google Drive → Qdrant
```

---

## 9. Seguridad

| Aspecto | Solución |
|---|---|
| ACL Odoo | Todos los tools usan `env` del usuario autenticado (nunca `sudo()`) |
| API keys | Variables de entorno en `.env`, nunca en código ni en versión |
| Acceso red | `helipistas-mcp` solo accesible internamente (sin puerto host expuesto) |
| Google Drive | Service Account con permisos de solo lectura |
| Historial chat | Almacenado en el frontend (OWL state), no en servidor |

---

## 10. Fases y estado

| Fase | Descripción | Estado |
|---|---|---|
| 1 | Módulo Odoo: scaffold, sidebar OWL, res.config.settings | Implementado — pendiente prueba |
| 2 | Docker: ai-service + helipistas-mcp + litellm + qdrant | **En curso** |
| 3 | helipistas-mcp: 6 tools reales + RAG normativas | Pendiente |
| 4 | Controlador Odoo simplificado (proxy HTTP) | Pendiente |
| 5 | Google Drive RAG + gdrive-indexer | Planificado |
| 6 | Audit log, métricas, optimización tokens | Planificado |

---

## 11. Decisiones arquitectónicas registradas

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-04-16 | LiteLLM como capa de abstracción de proveedores | Cambiar modelo = editar config.yaml, sin tocar código |
| 2026-04-16 | MCP custom (`helipistas-mcp`) en lugar de MCP genérico de Odoo | Los MCP genéricos no conocen los módulos leulit_*; necesitamos tools del dominio Helipistas |
| 2026-04-16 | FastMCP para el servidor MCP | Reduce boilerplate; @tool/@resource/@prompt como decoradores |
| 2026-04-16 | Qdrant para RAG | Ligero, open-source, Docker-native, sin dependencias cloud |
| 2026-04-16 | Google Drive en Fase 5 (no Fase 1) | No bloquear primera versión funcional; arquitectura ya preparada para ello |
| 2026-04-16 | ai-service como orquestador externo (no dentro de Odoo) | Permite escalar el servicio IA independientemente de Odoo; facilita pruebas locales |
