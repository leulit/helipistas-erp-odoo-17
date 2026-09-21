# leulit_ia — Búsqueda universal con IA

Barra de búsqueda en lenguaje natural sobre los datos de Odoo (botón en la barra
superior). La IA elige modelos y campos, y el módulo ejecuta la consulta con el ORM
del usuario, así que se respetan sus permisos. Sustituye al antiguo asistente de chat
de `leulit_ia` y al módulo `leulit_ai` (mismo código, renombrado).

## Qué incluye
- Búsqueda y agregaciones en lenguaje natural (límite duro de 100 registros).
- Favoritos (`leulit_ia.search.favorite`) e informes con visualización (`leulit_ia.search.report`).
- Motor: `leulit_ia.search.engine` (`models/ai_search.py`). Endpoints JSON en `/leulit_ia/*` (`controllers/main.py`, `auth='user'`).

## Proveedores de IA
Se elige en Ajustes → Leulit AI Search.
- **OpenRouter** (por defecto): parámetro `leulit_ia.openrouter_api_key`, modelo `anthropic/claude-3.7-sonnet`.
- **Vertex AI (Gemini)**: `leulit_ia.vertex_project_id`, `vertex_region` (def. `europe-west4`), `vertex_allowed_models`. Modelo por defecto `gemini-1.5-flash`; el motor lo usa con function calling (máx. 5 llamadas).

Las claves viven en `ir.config_parameter`, nunca en git.

## Instalación
1. Dependencias Python en el contenedor Odoo: `requests`, `google-cloud-aiplatform` (Vertex).
2. Vertex: copiar `vertex_service_account.json.example` a `vertex_service_account.json` (misma carpeta), con el JSON real de una Service Account con rol IAM *Vertex AI User*. Está en `.gitignore`: no commitear.
3. `./upd_module.sh leulit_ia dev --install` (primera vez; tiene modelos nuevos).
4. Configurar el proveedor en Ajustes.

## Pruebas
`docker exec -ti helipistas_odoo_17 odoo -u leulit_ia -d <db> --test-enable --test-tags=/leulit_ia --stop-after-init`

## Pendiente de revisar
- El manifiesto y la descripción dicen "Odoo 18.0", pero este repo es Odoo 17. Sin verificar que instale y funcione en 17.
- `security/ir.model.access.csv` da `base.group_user` lectura/escritura/creación sobre el motor: revisar qué implica para usuarios no técnicos.
