# Plan de Implementación: módulo `leulit_ia`

> Última actualización: 2026-04-16
> Ver arquitectura detallada en: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Visión

El módulo `leulit_ia` integra un asistente IA directamente en la interfaz de Odoo 17 Community.
El usuario escribe en lenguaje natural dentro de Odoo y recibe respuestas cruzando datos de múltiples módulos — sin saber qué módulo tiene el dato, sin exportar a Excel, sin esperar a que alguien conteste.

**Principio irrenunciable:** cada funcionalidad debe mejorar el trabajo diario del usuario. No se desarrolla IA por moda tecnológica.

---

## Arquitectura de contenedores

La solución corre íntegramente en Docker. Los contenedores existentes (Odoo + PostgreSQL) se complementan con nuevos servicios:

| Contenedor | Imagen | Rol |
|---|---|---|
| `helipistas_psql_15` | `postgres:15` | Base de datos — **ya existe** |
| `helipistas_odoo_17` | `wbms/odoo-17.0` | Odoo 17 Community — **ya existe** |
| `ai-service` | custom FastAPI | Orquestador: recibe prompt, gestiona loop MCP |
| `helipistas-mcp` | custom FastMCP | Servidor MCP con tools del dominio Helipistas |
| `litellm-proxy` | `ghcr.io/berriai/litellm` | Router de modelos — proveedor-agnóstico |
| `ollama` | `ollama/ollama` | LLM local opcional (Qwen, Llama3, Mistral…) |
| `qdrant` | `qdrant/qdrant` | Vector DB para RAG (normativas, manuales) |

Independencia de proveedor: `ai-service` siempre habla OpenAI-format hacia `litellm-proxy`.
Cambiar de Claude a Ollama = editar una línea en `litellm/config.yaml`.

---

## Fases de implementación

### Fase 1 — Scaffold del módulo Odoo (COMPLETADO parcialmente)

**Estado:** archivos creados, pendiente de prueba en entorno.

Archivos creados:
- `__manifest__.py`, `__init__.py`
- `models/res_config_settings.py` — campos ia_provider, ia_claude_api_key, ia_ollama_url, ia_ollama_model, ia_temperature, ia_max_tokens + action_test_ia_connection()
- `views/res_config_settings_views.xml` — panel en Ajustes, solo admin
- `security/ir.model.access.csv` — cabecera (sin modelos propios en Fase 1)
- `models/ai_tool.py` — AiToolRegistry con tools iniciales
- `controllers/main.py` — ruta /ai/chat con loop de herramientas
- `static/src/components/AiChatSidebar/` — componente OWL completo

**Criterio de done:** módulo instala sin errores; panel de ajustes visible; chat sidebar aparece en systray.

---

### Fase 2 — Infraestructura Docker con servicios IA (EN CURSO)

Crear bajo `docker/`:

```
docker/
├── docker-compose.yml          # reescribir: corregir paths + añadir servicios IA
├── .env.example                # variables de entorno (API keys, puertos)
├── litellm/
│   └── config.yaml             # routing de modelos (Claude / Ollama / otros)
├── ai-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                 # FastAPI: orquesta prompt → MCP → LiteLLM → respuesta
├── helipistas-mcp/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── server.py               # FastMCP: @tool, @resource, @prompt
│   ├── odoo_client.py          # JSON-RPC client para leulit_* models
│   ├── rag.py                  # consultas a Qdrant
│   └── documents/              # seed: normativa 16 bravo, manuales operativos
└── odoo.conf                   # ya existe (no modificar)
```

**Corrección crítica pendiente:** `docker-compose.yml` actual tiene paths erróneos:
- `../config:/etc/odoo` → debe ser `./odoo.conf:/etc/odoo/odoo.conf`
- `../addons:/mnt/extra-addons` → debe ser `../../:/mnt/extra-addons`

**Criterio de done:** `docker compose up` levanta todos los servicios; `curl http://localhost:8001/health` retorna OK desde ai-service.

---

### Fase 3 — Servidor MCP Helipistas con tools reales

Implementar en `helipistas-mcp/server.py` las 6 tools de alto valor (ordenadas por ROI):

| Tool | Datos en Odoo | Valor |
|---|---|---|
| `get_pilot_hours(pilot, period)` | leulit_actividad (partes vuelo), hr.attendance | "¿Cuántas horas tiene el piloto X este mes?" |
| `get_expired_documents(helipuerto)` | leulit_helipuerto (documentos + caducidad) | "¿Qué helipuertos tienen documentación caducada?" |
| `get_pending_maintenance(base)` | leulit_taller, leulit_camo, project.task | "¿Qué mantenimiento está pendiente en la base Y?" |
| `get_training_compliance(employee)` | leulit_escuela, survey.user_input, hr.employee | "¿Qué empleados no tienen la formación al día?" |
| `check_regulation_16bravo(pilot)` | leulit_actividad + RAG normativa 16 bravo | "¿Están los pilotos cumpliendo la 16 bravo?" |
| `get_schedule(employee, dates)` | leulit_planificacion, resource.calendar, hr.leave | "¿Cómo está la planificación de la semana?" |

Recursos RAG (`@resource`):
- `normativa://16bravo` — texto completo de la normativa 16 bravo
- `manual://operaciones` — manual de operaciones interno
- `perfiles://formacion` — perfiles de formación por puesto

**Criterio de done:** los 6 tools retornan datos reales del ORM; la normativa 16 bravo está disponible como @resource.

---

### Fase 4 — Adaptación del controlador Odoo

Simplificar `controllers/main.py`: en lugar de llamar directamente a Claude/Ollama, actúa como proxy HTTP hacia `ai-service`.

```
Odoo controller → POST http://ai-service:8001/chat → ai-service orquesta todo
```

`res.config.settings` sigue guardando la URL del ai-service (configurable).

**Criterio de done:** el chat sidebar de Odoo funciona end-to-end a través del ai-service containerizado.

---

### Fase 5 — Google Drive / Google Workspace (RAG documental)

Integración con Google Workspace para nutrir el RAG con documentación de empresa:

- `gdrive-indexer`: servicio que crawlea Google Drive periódicamente y indexa documentos en Qdrant
- `helipistas-mcp` expone `@resource gdrive://...` para búsqueda semántica
- Autenticación: Service Account de Google (JSON key en volumen secreto)

Casos de uso habilitados:
- "¿Qué procedimientos hay que actualizar si cambia la regulación X?"
- "¿Cuál es la versión vigente del manual de operaciones?"
- Detección de inconsistencias entre documentos relacionados

**Criterio de done:** una pregunta sobre documentación de empresa retorna contenido de Google Drive sin que el usuario sepa dónde está almacenado.

---

### Fase 6 — Auditoría, observabilidad y optimización

- Modelo `ai.chat.log` en Odoo: user_id, prompt, response, tool_calls, tokens_used, provider, create_date
- Vista lista del log en menú de configuración (solo admin)
- Métricas en ai-service: tiempo de respuesta, tokens por query, % de tool_calls
- Caché de tool_definitions en helipistas-mcp (evitar reconstruir JSON Schema por request)
- Manejo de errores: timeout LLM → mensaje amigable; tool falla → error descriptivo en contexto

**Criterio de done:** cada consulta queda registrada; tiempo de respuesta < 5s en queries sin herramientas; admins pueden auditar el uso.

---

## Casos de uso prioritarios (por impacto en el usuario)

1. **Horas piloto** — "¿Cuántas horas tiene acumuladas el piloto X este mes?"
2. **Documentación caducada** — "¿Qué helipuertos tienen la documentación caducada?"
3. **Mantenimiento pendiente** — "¿Qué tareas de mantenimiento están pendientes en la base Y?"
4. **Formación obligatoria** — "¿Qué empleados no han completado la formación obligatoria?"
5. **Cumplimiento 16 bravo** — "¿Están los pilotos cumpliendo con la 16 bravo?"
6. **Planificación** — "¿Cómo está la planificación de calendarios y horarios?"

---

## Verificación end-to-end

1. `docker compose up` — todos los servicios healthy
2. Configurar proveedor en Ajustes → "Probar conexión" → notificación verde
3. Abrir cualquier módulo de Odoo → ícono IA (robot morado) en systray → chat funcional
4. Preguntar "¿Cuántas horas tiene el piloto García este mes?" → respuesta con datos reales del ORM
5. Cambiar `litellm/config.yaml` a Ollama → misma pregunta → misma respuesta, distinto modelo
6. Usuario restringido → NO ve datos fuera de sus permisos (ACL Odoo respetado)
7. Revisar `ai.chat.log` → consulta registrada con tokens y herramienta usada
