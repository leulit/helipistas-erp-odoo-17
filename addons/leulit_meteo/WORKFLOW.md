# Flujo de Trabajo - leulit_meteo

Este documento describe la **arquitectura interna** y los **flujos de cada caso de uso** del módulo. Para instalación ver `INSTALL.md`, para guía paso a paso ver `USAGE.md`, para descripción funcional ver `README.md`.

---

## 1. Arquitectura del módulo

Visión general (selección de ubicación + obtención de datos + visualización):

```
┌──────────────────────────────────────────────────────────────┐
│  SELECCIÓN DE UBICACIÓN (input)                              │
│  Widget Leaflet + OpenStreetMap                              │
│  → produce: lat/lon (punto único) o lista de waypoints       │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  OBTENCIÓN DE DATOS (REST)                                   │
│  Servicios Python:                                           │
│    · OpenMeteoService                                        │
│    · WindyService                                            │
│    · AemetOpenDataService                                    │
│  → escribe campos en modelos Odoo                            │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  VISUALIZACIÓN (output)                                      │
│  · Tabla de puntos (datos numéricos)                         │
│  · Resumen computado (temp min/max, viento máx)              │
│  · Iframe Windy (overlay animado, no extrae datos)           │
└──────────────────────────────────────────────────────────────┘
```

Punto clave: **selección, datos y visualización son piezas independientes**. La visualización Windy (iframe) no consume datos del módulo; los servicios REST no usan el iframe.

### 1.1 Arquitectura del subsistema METAR — 4 capas

El subsistema METAR está diseñado para que cambiar o añadir proveedores no toque ni el modelo ni las vistas:

```
┌──────────────────────────────────────────────────────────────┐
│  CAPA 1 — Presentación / persistencia                        │
│  Modelo `leulit.meteo.metar` + sus vistas y menú             │
│  Independiente del proveedor concreto.                       │
│  Campo `provider = Selection(provider_selection())` decide   │
│  qué clase de la capa 2 se invoca.                           │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  CAPA 1b — Datos de referencia                               │
│  Tabla `leulit.meteo.icao.reference`                         │
│  Mapeo OACI ↔ FIR; opcional redirección de helipuertos       │
│  (tiene_metar_propio=False → ref_icao) al aeródromo          │
│  más cercano con METAR. El proveedor la consulta vía          │
│  `env['leulit.meteo.icao.reference'].resolve(icao)`.         │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  CAPA 2 — Proveedores                                        │
│  Interfaz `MetarProvider` + registro `@register_provider`    │
│    · AemetMetarProvider     (code='aemet')                   │
│    · (futuros: Aviation Weather, etc.)                       │
│  Cada proveedor devuelve el esquema normalizado:             │
│  provider, icao, icao_consultar, usa_referencia, ref_icao,   │
│  ref_nombre, fir_code, station_name,                         │
│  raw_metar, raw_taf, raw_sigmet,                             │
│  observation_time (parseo best-effort via capa 2b),          │
│  temperatura, dewpoint, wind_*, visibility_m, qnh.           │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  CAPA 2b — Parser METAR (best-effort)                        │
│  `leulit_meteo_metar_parser.parse_metar(raw)`                │
│  Extrae observation_time, viento, visibilidad, T/Td, QNH     │
│  del RAW. Nunca modifica el texto original. Usado por los    │
│  proveedores para poblar los campos numéricos derivados.     │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  CAPA 3 — Cliente HTTP                                       │
│  Clases que conocen el detalle de cada API REST              │
│    · AemetOpenDataService   (usado por AemetMetarProvider)   │
└──────────────────────────────────────────────────────────────┘
```

Para cambiar de fuente solo hace falta tocar la **capa 2** (añadir o reemplazar un `MetarProvider`); si la nueva fuente requiere un cliente HTTP propio, se añade en la **capa 3**. Las capas 1, 1b y 2b nunca cambian.

---

## 2. Casos de uso y flujos

### 2.1 Open-Meteo (punto único)

```
[Leaflet] click → lat/lon
   │
   ▼
[Form] fuente_datos = open_meteo
   │
   ▼
action_consultar_open_meteo()
   │
   ▼
OpenMeteoService → GET https://api.open-meteo.com/v1/forecast
   │
   ▼
Escribe campos: temperatura, viento, humedad, precipitación...
```

Sin API key. Para clima general y pronóstico básico.

### 2.2 Windy (punto único o polilínea)

```
[Leaflet] click(s) → lat/lon o waypoints
   │
   ▼
[Form] fuente_datos = windy
   │
   ▼
action_consultar_windy()
   │
   ├── punto único: 1 POST a Windy REST
   └── polilínea:   N POST (uno por waypoint en puntos_ids)
   │
   ▼
WindyService → POST https://api.windy.com/api/point-forecast/v2
   │  (header: api_key)
   ▼
Escribe datos en consulta o en cada leulit.meteo.consulta.punto
   │
   ▼
Pestaña "Mapa Windy Visual" carga iframe embed.windy.com (visual)
```

Requiere API key Windy en parámetros del sistema. El iframe se muestra **independientemente** de si la API REST se ha llamado.

### 2.3 Polilínea/ruta con plantillas

```
[Plantilla] leulit.meteo.ruta.template (waypoints predefinidos)
   │
   ▼
[Consulta nueva] selector "Cargar Ruta Predefinida" → action_cargar_ruta
   │
   ▼
Se copian puntos de la plantilla a puntos_ids
   │
   ▼
(Opcional) Editar en mapa Leaflet (drag, añadir, eliminar)
   │
   ▼
Consultar Windy/Open-Meteo (ver flujos anteriores)
   │
   ▼
(Opcional) "Guardar como Plantilla" → crea nueva ruta_template
```

Pensado para rutas de vuelo recurrentes.

### 2.4 Botón "Obtener briefing" — flujo completo

Modelo: `leulit.meteo.metar`. Capa de proveedores: `MetarProvider` (interfaz) + `AemetMetarProvider` (implementación actual). Referencia de aeródromos: `leulit.meteo.icao.reference`. Cliente HTTP: `AemetOpenDataService`. Parser: `leulit_meteo_metar_parser`.

```
[Form] provider = "aemet", icao = "LEUL"   (helipuerto sin METAR propio)
   │
   ▼
Usuario pulsa "Obtener briefing"
   │
   ▼
action_obtener_briefing()
   ├─ Valida: icao_code presente, 4 letras, alfabético
   └─ get_provider(self.provider) → AemetMetarProvider
   │
   ▼
AemetMetarProvider.get_observation(env, icao_code='LEUL')
   │
   ▼
leulit.meteo.icao.reference.resolve('LEUL')
   → icao_consultar='LELL', fir='LECB', usa_referencia=True, ref_nombre='Sabadell'
   (si OACI no está en tabla: icao_consultar=icao_code, fir=None,
    usa_referencia=False — SIGMET no disponible)
   │
   ▼
── RAMA PRINCIPAL: AEMET OpenData ──────────────────────────────────────────
   │
   │  Para cada mensaje, AemetOpenDataService usa el patrón 2 llamadas:
   │    ① _request_meta()  → GET .../mensajes/tipomensaje/{TIPO}/id/{OACI}?api_key=JWT
   │                         ← JSON con campo "datos" (URL temporal preautenticada)
   │    ② _fetch_text()    → GET <URL datos>
   │                         ← texto plano RAW (METAR / TAF / SIGMET)
   │
   ├─► get_message('METAR',  'LELL', api_key)  → raw_metar  (o None)
   ├─► get_message('TAF',    'LELL', api_key)  → raw_taf    (o None)
   └─► get_message('SIGMET', 'LECB', api_key)  → raw_sigmet (o None si fir=None)
   │
   ▼
¿AEMET devolvió datos?
   │
   ├─ SÍ ─────────────────────────────────────────────────────────────────►─┐
   │                                                                         │
   └─ NO → FALLBACK 1: CheckWX ─────────────────────────────────────────────┤
              CheckWXService.get_metar(icao_consultar)                       │
              CheckWXService.get_taf(icao_consultar)                         │
              GET https://api.checkwx.com/metar/{OACI}?token=<key>          │
              GET https://api.checkwx.com/taf/{OACI}?token=<key>            │
                                                                             │
              ¿hay station_code en el registro?                              │
                 SÍ → FALLBACK 2: METAR sintético de estación AEMET ────────┤
                        get_observaciones_estacion(station_code)             │
                        latest_observation() → observación más reciente      │
                        build_metar_synthetic() → raw_metar_est              │
                        (texto NO oficial, identificado como "SYN")          │
                 NO → sin datos adicionales                                  │
                                                                             ▼
                                                              ┌──────────────────────────┐
                                                              │ dict normalizado del      │
                                                              │ proveedor:                │
                                                              │   raw_metar, raw_taf,     │
                                                              │   raw_sigmet, raw_metar_est│
                                                              │   fir_code, usa_referencia│
                                                              │   ref_icao, ref_nombre    │
                                                              │   station_name            │
                                                              └──────────────┬───────────┘
   │                                                                         │
   └─────────────────────────────────────────────────────────────────────────┘
   │
   ▼
parse_metar(raw_metar)   (best-effort, nunca altera el RAW)
   → observation_time, wind_direction, wind_speed_kt, wind_gust_kt,
     visibility_m, temperatura, dewpoint, qnh
   │
   ▼
_write_observacion(data)
   Escribe en el registro leulit.meteo.metar:
   · raw_metar, raw_taf, raw_sigmet   (textos oficiales, sin alterar — válidos AESA)
   · raw_metar_est                    (sintético AEMET, si disponible)
   · fir_code, usa_referencia, ref_icao, ref_nombre, station_name
   · observation_time, temperatura, dewpoint, wind_*, visibility_m, qnh
   · fecha_consulta = now()
   [campos computados: edad_datos_minutos, estado_datos se recalculan solos]
   │
   ▼
Notificación de éxito + recarga del formulario
Vista: aviso informativo visible si usa_referencia=True
```

**Campos leídos:** `icao_code`, `provider`, `station_code` (del registro); `leulit_meteo.aemet_api_key`, `leulit_meteo.checkwx_api_key` (de `ir.config_parameter`); tabla `leulit.meteo.icao.reference` (tiene_metar_propio, ref_icao, fir, station_code).

**Campos escritos:** todos los listados en `_write_observacion` arriba. El RAW prevalece siempre; los campos numéricos son auxiliares.

---

### 2.5 Integración con leulit.vuelo

El módulo `leulit_vuelo` hereda de `leulit_meteo` para añadir meteorología automática al parte de vuelo. El registro `leulit.meteo.metar` creado en el flujo 2.4 se vincula al vuelo vía `Many2one`.

#### 2.5.1 Obtención manual de meteorología

```
[leulit.vuelo — formulario del parte]
   │
   ▼
Usuario pulsa "Obtener meteorología salida"
   │
   ▼
action_obtener_meteo_salida()
   ├─ Lee: vuelo.aerodromo_salida_id.codigo_oaci  (ej. 'LEUL')
   │
   └─ Opción A — método simplificado (recomendado):
        self.env['leulit.meteo.metar'].briefing_oaci(icao)
        → busca/crea registro leulit.meteo.metar para ese OACI
        → ejecuta el flujo completo de la sección 2.4
        → devuelve: {record_id, raw_metar, raw_taf, raw_metar_est,
                      historico, observation_time,
                      provider, metar_icao, usa_referencia}

      Opción B — método clásico:
        self.env['leulit.meteo.metar'].obtener_metar(
            icao_code=icao, provider='aemet', persistir=True)
        → ejecuta el flujo completo de la sección 2.4
        → devuelve dict completo del proveedor + record_id
   │
   ▼
vuelo.metar_salida_id = data['record_id']
   │
   ▼
_compute_estado_meteo()  [campo computado; se recalcula automáticamente]
   (ver sección 2.5.2)
```

#### 2.5.2 Evaluación automática de condiciones (campo computado)

```
metar_salida_id modificado
   │
   ▼
_compute_estado_meteo()
   ├─ Lee umbrales: LeulitMeteoUmbralConfig.get_umbrales(env)
   ├─ Lee del METAR vinculado:
   │     wind_speed_kt, wind_gust_kt, visibility_m
   │
   └─ Clasifica → estado_meteo:
        'nogo'     si viento > umbral_nogo
                   OR rachas > umbral_nogo
                   OR visibilidad < min_nogo
        'marginal' si viento > umbral_marginal
                   OR rachas > umbral_marginal
                   OR visibilidad < min_marginal
        'ok'       dentro de límites aceptables
        'sin_datos' si metar_salida_id está vacío o sin observación
```

#### 2.5.3 Campos añadidos a leulit.vuelo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `metar_salida_id` | Many2one → `leulit.meteo.metar` | METAR del aeródromo de salida |
| `estado_meteo` | Selection (computado, stored) | Resultado de la evaluación de condiciones |

**Campos leídos:** `aerodromo_salida_id.codigo_oaci`; umbrales de configuración; `metar_salida_id.wind_speed_kt`, `.wind_gust_kt`, `.visibility_m`.

**Campos escritos:** `metar_salida_id` (ID del registro METAR creado/actualizado); `estado_meteo` (computado automáticamente al cambiar `metar_salida_id`).

#### 2.5.4 Automatización opcional en autorización de vuelo

```
action_autorizar_vuelo()
   ├─ action_obtener_meteo_salida()   (silenciando errores de red)
   └─ vuelo.state = 'autorizado'
```

Permite que la meteorología se capture de forma transparente al autorizar, sin que el usuario tenga que pulsar el botón explícitamente.

---

## 3. Componentes clave

### Widget Leaflet (INPUT)

- Ficheros: `static/src/js/meteo_map_widget.js`, `meteo_map_widget.css`, `meteo_map_widget.xml`.
- Mapa OpenStreetMap embebido en formulario Odoo.
- Modos: punto único o polilínea (varios markers + línea conectora).
- Interacción: click izquierdo añade marker, drag mueve marker, click derecho elimina marker.
- Botones: limpiar, centrar, guardar ruta.
- **No** muestra meteo. **No** requiere API key.

### Iframe Windy (OUTPUT visual)

- Pestaña "Mapa Windy Visual" en el formulario de `leulit.meteo.consulta`.
- URL generada por `get_windy_embed_url()` en el modelo.
- Base: `https://embed.windy.com/embed2.html` con parámetros (lat, lon, zoom, overlay, product, métricas).
- Overlay animado (viento, temperatura, nubes, precipitación, presión).
- **Solo visualización**: no extrae datos al modelo. Embed público, sin API key.

### Plantillas de ruta

- Modelo: `leulit.meteo.ruta.template` (cabecera) + `leulit.meteo.ruta.template.punto` (waypoints).
- Biblioteca reutilizable. Se copia a `puntos_ids` de la consulta cuando se carga.

### Servicios Python (REST)

| Servicio                  | Llama a                                                        | Método |
| ------------------------- | -------------------------------------------------------------- | ------ |
| `OpenMeteoService`        | `https://api.open-meteo.com/v1/forecast`                       | GET    |
| `WindyService`            | `https://api.windy.com/api/point-forecast/v2`                  | POST   |
| `AemetOpenDataService`    | `https://opendata.aemet.es/opendata/api/...` (+ URL `datos`)   | GET×2  |

### Modelos Odoo

- `leulit.meteo.consulta` — cabecera de consulta. Campos relevantes: `fuente_datos`, `es_polilinea`, `ruta_template_id`, `puntos_ids`, resúmenes computados.
- `leulit.meteo.consulta.punto` — waypoint individual con sus datos meteo.
- `leulit.meteo.ruta.template` + `leulit.meteo.ruta.template.punto` — plantillas reutilizables.
- `leulit.meteo.metar` — reporte METAR/TAF/SIGMET independiente de proveedor (ver 2.4). Campo `provider` selecciona la fuente; hoy solo `aemet`.
- `leulit.meteo.icao.reference` — tabla de aeródromos OACI ↔ FIR; permite redirigir helipuertos sin METAR propio al aeródromo de referencia más cercano.

---

## 4. Mapa Leaflet vs Iframe Windy

Confusión habitual: ambos parecen "el mapa", pero hacen cosas opuestas.

| Aspecto             | Mapa Leaflet                | Iframe Windy                       |
| ------------------- | --------------------------- | ---------------------------------- |
| Rol                 | INPUT (selección)           | OUTPUT (visualización)             |
| Tecnología          | Leaflet + OpenStreetMap     | `embed.windy.com/embed2.html`      |
| Interacción         | Click marca/edita puntos    | Solo zoom, pan, cambio de capa     |
| Overlay meteo       | No                          | Sí (animado: viento, temp, nubes…) |
| Modifica el modelo  | Sí (escribe lat/lon)        | No                                 |
| API key necesaria   | No                          | No (embed público)                 |
| Ubicación en form   | Sección "Mapa Interactivo"  | Pestaña "Mapa Windy Visual"        |

---

## 5. APIs externas

| API                     | URL base                                                       | Key requerida | Operadora         | Uso en el módulo                   |
| ----------------------- | -------------------------------------------------------------- | ------------- | ----------------- | ---------------------------------- |
| Open-Meteo              | `https://api.open-meteo.com/v1/forecast`                       | No            | Open-Meteo        | Datos meteo generales              |
| Windy REST              | `https://api.windy.com/api/point-forecast/v2`                  | Sí            | Windyty SE        | Punto-forecast por waypoint        |
| Windy Embed (iframe)    | `https://embed.windy.com/embed2.html`                          | No            | Windyty SE        | Visualización rica con overlay     |
| AEMET OpenData          | `https://opendata.aemet.es/opendata`                           | Sí (JWT)      | AEMET (España)    | Mensajes oficiales METAR/TAF/SIGMET por OACI o FIR. RAW intacto. |

Notas:

- **AEMET OpenData** usa un patrón de dos llamadas: la primera devuelve un JSON con un campo `datos` que es a su vez una URL temporal donde están los datos reales.

---

## 6. Preguntas frecuentes

**¿Por qué hay dos mapas?**
El de Leaflet sirve para que tú selecciones la ubicación (input). El iframe de Windy sirve para que veas las condiciones meteorológicas con overlay animado (output). Hacen cosas opuestas.

**¿AEMET ofrece METAR oficiales?**
Sí. AEMET OpenData publica mensajes oficiales METAR, TAF y SIGMET por OACI y FIR respectivamente. El módulo los descarga y guarda el texto **sin modificar** (`raw_metar`, `raw_taf`, `raw_sigmet`), válido a efectos legales/AESA. Los campos numéricos decodificados son auxiliares y obtenidos por parsing best-effort.

**¿Necesito API key para el iframe de Windy?**
No. El embed (`embed.windy.com/embed2.html`) es público. La API key de Windy solo se requiere para la API REST (`api.windy.com/api/point-forecast/v2`).

**¿Qué pasa si AEMET no devuelve datos para un OACI?**
La acción `action_obtener_briefing()` lanza un `UserError`. Causas habituales: aeródromo sin servicio MET activo, AEMET sin publicación en ese momento, o API key incorrecta. Si el OACI es un helipuerto sin METAR propio, asegúrate de que esté dado de alta en **Aeródromos de Referencia** con un `ref_icao` correcto.

**¿Cómo añado un helipuerto o aeródromo nuevo?**
Ir a **Meteorología → Aeródromos de Referencia** (solo administradores) y crear un registro. Indicar FIR (LECM/LECB/GCCC) y, si el punto no emite METAR propio, desmarcar `tiene_metar_propio` y rellenar `ref_icao` con el OACI del aeródromo cercano. No hay que tocar ningún fichero Python.

**¿Cómo cambio de proveedor de METAR?**
Selecciona otro valor en el campo **Proveedor** del registro `leulit.meteo.metar`. Para añadir un proveedor nuevo, crea una subclase de `MetarProvider` decorada con `@register_provider` e impórtala en `models/__init__.py`. El modelo, las vistas y el menú no necesitan cambios: el nuevo `code` aparece automáticamente en el selector.
