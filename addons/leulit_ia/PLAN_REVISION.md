# Revisión de código — `leulit_ia`

Revisión estática (sin entorno Odoo disponible) de todo el addon `addons/leulit_ia/` a fecha 2026-09-10.
Se ha leído primero `CLAUDE.md` y `ARCHITECTURE.md` del propio módulo y se han seguido sus convenciones.

Comprobación explícita pedida en la nota del módulo: **no se ha encontrado ninguna referencia a modelos/módulos
Enterprise** (`sign`, `documents`, `web_gantt`, `web_studio`, `loyalty.program`, `planning.slot`, etc.) en
`leulit_ia/`. El `__manifest__.py` solo depende de `base`, `mail`, `web`. Este punto queda cerrado, sin hallazgo.

## 1. Resumen ejecutivo

- **Críticos: 1** — bug reproducible (verificado con un script Python) que provoca un `TypeError` no controlado
  en el camino de "no se pudo completar la consulta".
- **Altos: 4** — dependencias de manifest que faltan, endpoint de coste/recursos sin control de acceso ni límites,
  ausencia de timeout en la llamada a Claude, y pérdida silenciosa de tool-calls paralelos.
- **Medios: 5** — inconsistencia de modelo Claude entre "probar conexión" y chat real, valores de estado
  hardcoded no verificables sin ejecutar, fuga de excepciones crudas al usuario, renderer Markdown frágil,
  y `_normalize_messages_for_claude` sin defensas ante historial manipulado por el cliente.
- **Bajos: 4** — detalles de mantenibilidad/consistencia (secrets de dev versionados, CSV de ACL vacío,
  `csrf=False` redundante, modelo Claude no configurable).

El hallazgo más grave (C1) es puramente interno del módulo y 100% verificable por lectura + repro en Python
puro. Los dos siguientes en gravedad (A1, A2) son de alcance/paquete (`__manifest__.py`) y de superficie de
ataque de coste (endpoint `/ai/chat` sin restricción de grupo ni límites), coherentes con que este módulo
maneja credenciales de pago (Claude API) y toca datos de RRHH/proyectos/encuestas.

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `controllers/main.py:41,84-85` | `for _ in range(...)` reasigna `_` (la función de traducción importada) al índice del bucle; en la rama `else` del `for` se llama `_('Lo siento…')` sobre un `int` | El LLM encadena 5 rondas de `tool_use` sin llegar nunca a `type=='text'` (bucle no converge) | Renombrar la variable del bucle a algo que no colisione con `_`, p.ej. `for _iteration in range(...)` |
| Alto | `__manifest__.py:10-14` + `models/ai_tool.py:134,162,187` | `depends` solo incluye `base`, `mail`, `web`, pero las tools usan `survey.user_input`, `project.task`, `hr.employee` | Instalación de `leulit_ia` en una BD sin `project`/`survey`/`hr` instalados (o desinstalación futura de esos módulos) | Añadir `'project'`, `'survey'`, `'hr'` a `depends` en `__manifest__.py` |
| Alto | `controllers/main.py:17-38` | Ruta `/ai/chat` con `auth='user'` sin ninguna comprobación de grupo, cuota o límite de tamaño de `conversation_history`; cada request puede disparar hasta 5 llamadas de pago a Claude | Cualquier usuario autenticado (incluido portal si el registro tiene sesión válida) hace POST directo a `/ai/chat` con un `conversation_history` arbitrariamente grande y/o en bucle | Comprobar grupo (`request.env.user.has_group(...)`) al inicio de `chat()`, y acotar/truncar `conversation_history` antes de procesarlo |
| Alto | `controllers/main.py:180-188` | `anthropic.Anthropic(...).messages.create(...)` sin `timeout` explícito; combinado con hasta 5 iteraciones por request, puede bloquear un worker de Odoo durante minutos | La API de Anthropic tarda o se queda colgada (red lenta, incidente del proveedor) | Pasar `timeout=` al cliente o a la llamada (según versión del SDK `anthropic` instalado — ver Dudas) |
| Alto | `controllers/main.py:191-199` | Solo se procesa el **primer** bloque `tool_use` de `response.content`; si Claude pide varias tools en paralelo en el mismo turno, el resto se descarta en silencio | El LLM responde con 2+ bloques `tool_use` en la misma respuesta (tool-calling paralelo, soportado por la API de Claude) | Iterar todos los bloques `tool_use`, ejecutar cada tool y devolver todos los `tool_result` emparejados por `id` (requiere adaptar también `_normalize_messages_for_claude` a tool_use plural) |
| Medio | `models/res_config_settings.py:87` vs `controllers/main.py:182` | `action_test_ia_connection` prueba `claude-3-haiku-20240307`; el chat real usa `claude-3-5-haiku-20241022` (hardcoded, no configurable) | "Probar conexión" da OK/KO que no refleja necesariamente el modelo realmente usado en el chat (o viceversa si uno de los dos se deprecia) | Unificar en una única constante/config (`ia_claude_model`, con default) usada por ambos paths |
| Medio | `models/ai_tool.py:155-158` | Domain hardcoded `('state', 'not in', ['1_done', 'cancel'])` sobre `project.task` — valor `'cancel'` no verificable sin ejecutar (ver Dudas) | Si el valor real de "cancelada" en `project.task.state` no es literalmente `'cancel'`, las tareas canceladas se seguirán reportando como "retrasadas" | Verificar contra la selección real del campo en esta instancia; si difiere, corregir el literal (cambio fuera de alcance de `leulit_ia` en cuanto a modelo, pero el literal sí vive aquí) |
| Medio | `models/ai_tool.py:113-117` | `except Exception as e: return {'error': str(e)}` reenvía el texto crudo de la excepción Python al LLM/usuario final | Cualquier error interno (campo inexistente, error de ORM, etc.) al ejecutar una tool | Loguear el detalle completo con `_logger.exception` (ya se hace) y devolver al usuario un mensaje genérico, no `str(e)` |
| Medio | `static/src/components/AiChatSidebar/AiChatSidebar.js:104-135` | `renderMarkdown` aplica regex secuenciales sin proteger `code`/`pre`; el contenido de un code-span puede ser re-procesado por las regex de negrita/cursiva; los headers quedan anidados dentro de un `<p>` final | Respuesta del asistente con code inline que contiene `**`/`_`/`#`, o con headers `##` | Extraer bloques `code`/`pre` a placeholders antes de aplicar el resto de reglas y reinsertarlos al final; no envolver bloques ya convertidos en `<h3>`/`<ul>`/`<pre>` dentro de un `<p>` extra |
| Medio | `controllers/main.py:284-334` | `_normalize_messages_for_claude` asume emparejamiento rígido `assistant(tool_use)` seguido inmediatamente de `tool` en `messages[i+1]`, sin validar forma, y `conversation_history` viene del cliente sin validar (ligado al hallazgo Alto de arriba) | Un cliente que envíe un `conversation_history` manipulado/reordenado (bug de frontend o request manual) hace que `tool_result_msg` sea `None` o el mensaje equivocado → `TypeError`/`KeyError` al acceder a `['content']` | Validar la forma del mensaje siguiente antes de usarlo; si no cumple el patrón esperado, tratarlo como error controlado en vez de excepción cruda |
| Bajo | `docker/odoo.conf:5,11` | `admin_passwd = helipistas`, `db_password = odoo` en claro y versionados en git (consistente con el resto del repo, pero contradice lo que dice el propio `ARCHITECTURE.md` sobre `.env` no versionado) | N/A (config de dev) | Confirmar con el usuario si se acepta como está (mismo patrón que `config/odoo.conf` raíz) o se migra a `.env` |
| Bajo | `security/ir.model.access.csv:1` | Fichero con solo cabecera, sin filas — inofensivo hoy porque `ai.tool.registry` es `AbstractModel` (sin tabla), pero quedará pendiente el día que se añada un modelo real (p.ej. `ai.chat.log` de la Fase 6) | Instalación de un futuro modelo concreto sin recordar añadir sus reglas de acceso | Nota para cuando se implemente la Fase 6: añadir filas de ACL (y `ir.rule` si aplica) en ese momento |
| Bajo | `controllers/main.py:17` | `csrf=False` explícito en una ruta `type='json'` — redundante, las rutas JSON-RPC de Odoo no usan el mismo mecanismo CSRF que `type='http'` | N/A | Quitar el parámetro o documentar por qué se fuerza explícitamente |
| Bajo | `controllers/main.py:182` / `models/res_config_settings.py` | Modelo de Claude fijo en código pese a que `ia_temperature`/`ia_max_tokens`/`ia_ollama_model` sí son configurables — inconsistencia de diseño | N/A | Añadir `ia_claude_model` como campo configurable análogo a `ia_ollama_model` |

## 3. Hallazgos críticos/altos desarrollados

### C1 — `TypeError` al agotar las iteraciones de tool-calling (`controllers/main.py`)

**Código actual:**

```python
# controllers/main.py
from odoo import http, _          # línea 6 — `_` es la función de traducción

...
MAX_TOOL_ITERATIONS = 5

...
for _ in range(MAX_TOOL_ITERATIONS):        # línea 41 — reasigna `_` al índice del bucle
    llm_response = self._call_llm(...)
    if llm_response['type'] == 'text':
        ...
        break
    if llm_response['type'] == 'tool_use':
        ...
else:
    response_text = _('Lo siento, no pude completar la consulta en el número máximo de pasos.')  # línea 85
```

**Por qué falla:** en Python, `for _ in range(N)` liga el nombre `_` al índice del bucle en el ámbito de la
función. Como `_` es también el nombre importado de `odoo._` (gettext), tras el bucle esa referencia queda
sobrescrita por un entero (el último valor de `range`). La rama `else` de un `for` se ejecuta cuando el bucle
termina **sin** `break` — exactamente el caso "se agotaron las 5 iteraciones sin respuesta de texto" que el
propio código intenta manejar con un mensaje amistoso. En ese momento, `_('Lo siento…')` intenta *llamar* a un
`int`, lo cual lanza `TypeError: 'int' object is not callable`.

Verificado de forma aislada (no requiere Odoo, es semántica pura de Python):

```python
def _(x):
    return "TRANSLATED: " + x

def demo():
    for _ in range(3):
        pass
    else:
        return _('hola')

demo()
# Traceback (most recent call last):
# TypeError: 'int' object is not callable
```

**Impacto:** el caso que este código intentaba cubrir con elegancia (avisar al usuario de que no se pudo
completar la consulta) es precisamente el que hace saltar una excepción no controlada. Odoo devolverá un error
JSON-RPC genérico en vez del mensaje en español previsto, y quedará traza en logs (o, según configuración de
depuración, visible al cliente).

**Fix propuesto:**

```python
for _iteration in range(MAX_TOOL_ITERATIONS):
    llm_response = self._call_llm(...)
    ...
else:
    response_text = _('Lo siento, no pude completar la consulta en el número máximo de pasos.')
```

Cambio mínimo de una palabra; no afecta a ninguna otra parte del método.

---

### A1 — Dependencias de manifest incompletas (`__manifest__.py` + `models/ai_tool.py`)

**Código actual:**

```python
# __manifest__.py
'depends': [
    'base',
    'mail',
    'web',
],
```

```python
# models/ai_tool.py
inputs = env['survey.user_input'].search(domain, limit=50)      # línea 134
...
tasks = env['project.task'].search(domain, limit=50)            # línea 162
...
employees = env['hr.employee'].search([...], limit=5)           # línea 187
```

**Por qué falla:** las tres tools registradas en `ai.tool.registry` usan modelos de `survey`, `project` y `hr`,
ninguno de los cuales está declarado en `depends`. `base`/`mail`/`web` no arrastran esos módulos de forma
transitiva. El error queda enmascarado en tiempo de ejecución porque `execute_tool()` envuelve la llamada en
`try/except Exception` (línea 113-117 de `models/ai_tool.py`), así que no habrá un crash visible — solo un
`{'error': "'project.task'"}` (o similar `KeyError`) devuelto al chat si esos módulos no estuvieran instalados.
En esta instancia de Helipistas es prácticamente seguro que `project`/`survey`/`hr` ya están instalados (otros
`leulit_*` dependen de ellos), por lo que el riesgo práctico inmediato es bajo — pero el manifest sigue siendo
incorrecto: el grafo de dependencias de Odoo no refleja la realidad, lo que afecta a orden de carga, a
verificaciones de "no desinstalar módulo X porque Y depende de él", y a la instalabilidad del módulo en una BD
limpia o de test.

**Fix propuesto (diff):**

```diff
 'depends': [
     'base',
     'mail',
     'web',
+    'project',
+    'survey',
+    'hr',
 ],
```

---

### A2 — `/ai/chat` sin control de acceso ni límite de tamaño de historial (`controllers/main.py`)

**Código actual:**

```python
@http.route('/ai/chat', type='json', auth='user', methods=['POST'], csrf=False)
def chat(self, prompt, conversation_history=None):
    if conversation_history is None:
        conversation_history = []
    config = self._get_config()
    ...
    conversation_history.append({'role': 'user', 'content': prompt})
    for _ in range(MAX_TOOL_ITERATIONS):
        llm_response = self._call_llm(messages=conversation_history, ...)
        ...
```

**Por qué es un problema:**
- `auth='user'` solo exige sesión autenticada; no hay ningún `has_group()`/chequeo de rol antes de ejecutar
  hasta `MAX_TOOL_ITERATIONS` llamadas a un proveedor de pago (Claude API) o a Ollama. No existe restricción
  para excluir, por ejemplo, usuarios portal (si su sesión llega a tener acceso al endpoint — ver Dudas D3).
- `conversation_history` se acepta tal cual del cliente y se reenvía íntegro (y creciente en cada turno) al
  LLM, sin cota de tamaño ni de número de mensajes. Un cliente (con bug o malicioso) puede mandar un array
  arbitrariamente grande en una sola llamada JSON-RPC.
- No hay ninguna cuota por usuario/día ni *rate limiting* a nivel de módulo.

Esto es relevante porque el propio diseño (ARCHITECTURE.md) reconoce que cada llamada cuesta dinero real
(Claude API) y que el historial "vive en el frontend" — es decir, el servidor confía en lo que el navegador le
manda.

**Fix propuesto (parcial, snippet):**

```python
from odoo.exceptions import AccessError

MAX_HISTORY_MESSAGES = 40  # ajustar según UX deseada

@http.route('/ai/chat', type='json', auth='user', methods=['POST'], csrf=False)
def chat(self, prompt, conversation_history=None):
    if not request.env.user.has_group('base.group_user'):
        raise AccessError(_('No tiene permiso para usar el asistente IA.'))

    if conversation_history is None:
        conversation_history = []
    if len(conversation_history) > MAX_HISTORY_MESSAGES:
        conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]
    ...
```

Una cuota por usuario/día (p.ej. contador en `ir.config_parameter` o un modelo dedicado) sería un paso
adicional razonable, pero excede lo que se puede resolver con un cambio puntual — se apunta en el plan de
acción como tarea separada.

---

### A3 — Sin timeout explícito en la llamada a Claude (`controllers/main.py:180-188`)

**Código actual:**

```python
client = anthropic.Anthropic(api_key=api_key)
response = client.messages.create(
    model='claude-3-5-haiku-20241022',
    max_tokens=config['max_tokens'],
    temperature=config['temperature'],
    system=system,
    messages=claude_messages,
    tools=claude_tools,
)
```

Compárese con `_call_ollama` (línea 253-257), que sí fija `timeout=60`. Si la API de Claude tarda o queda
colgada, cada una de las hasta 5 iteraciones del bucle de tool-calling puede bloquear el worker HTTP de Odoo
que atiende esa request durante el timeout por defecto del SDK (potencialmente varios minutos acumulados),
agravando el riesgo de agotamiento del pool de workers descrito en A2.

**Fix propuesto:**

```python
client = anthropic.Anthropic(api_key=api_key, timeout=30.0)
```

(o pasar `timeout=` en la propia llamada `.messages.create(...)`, según la versión exacta del SDK `anthropic`
instalado en el contenedor — ver Dudas D4).

---

### A4 — Solo se procesa el primer `tool_use` cuando Claude pide varias tools en paralelo (`controllers/main.py:191-199`)

**Código actual:**

```python
if response.stop_reason == 'tool_use':
    for block in response.content:
        if block.type == 'tool_use':
            return {
                'type': 'tool_use',
                'tool_name': block.name,
                'tool_input': block.input,
                'raw_content': response.content,
            }
```

**Por qué falla:** la API de Claude puede devolver varios bloques `tool_use` en un mismo turno (tool-calling
paralelo). Este código `return`ea en cuanto encuentra el primero, descartando silenciosamente el resto. El
resultado: si el modelo intenta, por ejemplo, pedir `get_project_delays` y `get_course_status` a la vez, solo
se ejecuta la primera; la segunda nunca se responde y su intención se pierde sin traza ni error visible —
simplemente el asistente da una respuesta incompleta.

**Fix propuesto (dirección, no trivial):** iterar todos los bloques `tool_use`, ejecutar cada tool con
`ai.tool.registry.execute_tool`, y construir un turno de `assistant` con **todos** los `tool_use` y el
siguiente turno de `user` con **todos** los `tool_result` correspondientes (emparejados por `id`). Esto exige
también adaptar `_normalize_messages_for_claude` (que hoy asume un único `tool_use` por mensaje `assistant`,
guardado como dict, no como lista) y el formato de historial persistido en `conversation_history`. Es un cambio
de forma de datos, no un one-liner — se recomienda abordarlo junto con la Fase 3/4 del roadmap
(`helipistas-mcp`), no como parche aislado, dado que ahí se rediseña de todos modos el bucle de tool-calling.

## 4. Plan de acción priorizado

1. **[Crítico]** `controllers/main.py:41` — renombrar la variable del bucle `for _ in range(...)` para dejar de
   sombrear la función de traducción `_`.
2. **[Alto]** `__manifest__.py:10-14` — añadir `project`, `survey`, `hr` a `depends`.
3. **[Alto]** `controllers/main.py:17-38` — añadir comprobación de grupo/permiso y cota de tamaño a
   `conversation_history` antes de procesar la petición.
4. **[Alto]** `controllers/main.py:180-188` — fijar `timeout` explícito en el cliente/llamada de Anthropic.
5. **[Alto]** `controllers/main.py:191-199` (+ `284-334`) — decidir con el usuario si se aborda ya el soporte
   de `tool_use` múltiple o se pospone a la Fase 3/4 (rediseño con `helipistas-mcp`); si se pospone, documentar
   la limitación conocida en `ARCHITECTURE.md`.
6. **[Medio]** `models/res_config_settings.py:87` + `controllers/main.py:182` — unificar el modelo Claude usado
   en "probar conexión" y en el chat real en una única constante/config.
7. **[Medio]** `models/ai_tool.py:155-158` — verificar contra la instancia real el valor de "cancelada" en
   `project.task.state` (ver Dudas D1) y corregir el literal si procede.
8. **[Medio]** `models/ai_tool.py:113-117` — no devolver `str(e)` crudo al usuario; mensaje genérico + log
   completo (ya existe `_logger.exception`, falta cambiar el `return`).
9. **[Medio]** `static/.../AiChatSidebar.js:104-135` — proteger `code`/`pre` de las regex posteriores y evitar
   anidar bloques ya convertidos dentro de un `<p>` final.
10. **[Medio]** `controllers/main.py:284-334` — validar la forma de `tool_result_msg` antes de usarla (defensa
    ante `conversation_history` manipulado desde el cliente).
11. **[Bajo]** `controllers/main.py:17` — quitar el `csrf=False` redundante en la ruta `type='json'`, o
    documentar el motivo si se mantiene a propósito.
12. **[Bajo]** Exponer `ia_claude_model` como campo configurable (paralelo a `ia_ollama_model`).
13. **[Bajo]** `docker/odoo.conf` — confirmar con el usuario si los credenciales de dev en claro se mantienen
    versionados (patrón ya existente en el resto del repo) o se migran a `.env`.
14. **[Bajo]** Dejar nota/recordatorio para cuando se implemente `ai.chat.log` (Fase 6): añadir sus filas a
    `security/ir.model.access.csv`.

## 5. Dudas / no verificable sin entorno

- **D1.** `models/ai_tool.py:157` — el valor exacto de "tarea cancelada" en la selección del campo
  `project.task.state` de la versión de `project` instalada en esta BD no se puede confirmar leyendo solo
  `leulit_ia/` (depende de un modelo de otro módulo, fuera de alcance para modificarlo aquí sin más contexto).
  Habría que comprobarlo en el entorno de pruebas real (p.ej. inspeccionando el campo desde la UI técnica o
  con `env['project.task']._fields['state'].selection`).
- **D2.** `models/ai_tool.py:142` — el nombre exacto del campo de fecha límite en `survey.user_input`
  (`date_deadline` en el código actual) no se ha podido confirmar contra el código fuente del módulo `survey`
  de Odoo 17 Community, que no está presente en este repo (es core, no vendorizado en
  `third-party-addons/`). Si el nombre real difiriera, la tool fallaría, pero quedaría capturada por el
  `try/except` de `execute_tool` (degradación controlada, no crash) — aun así conviene confirmarlo en el
  entorno de pruebas.
- **D3.** No se ha podido confirmar si, en esta instancia concreta de Helipistas, existen usuarios de tipo
  portal con sesión capaz de invocar `/ai/chat` directamente (fuera del systray, vía POST JSON-RPC directo), ni
  qué devolverían realmente los `ir.rule` de `project.task`/`hr.employee`/`survey.user_input` para ese perfil.
  Esto depende de la configuración de grupos y de otros módulos instalados, no verificable solo con lectura de
  `leulit_ia/`.
- **D4.** El comportamiento exacto del parámetro `timeout` en el SDK Python `anthropic` (a nivel de cliente vs.
  de llamada) depende de la versión exacta instalada en el contenedor (`docker exec ... pip show anthropic`),
  que no se puede ejecutar desde aquí.
- **D5.** El comportamiento exacto de Odoo ante `external_dependencies.python` cuando falta un paquete (si
  bloquea la instalación completa del módulo incluso si solo se piensa usar el proveedor Ollama) no se ha
  podido verificar ejecutando una instalación real.
