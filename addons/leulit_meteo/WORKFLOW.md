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

### 1.1 Arquitectura del subsistema METAR — 3 capas

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
│  CAPA 2 — Proveedores                                        │
│  Interfaz `MetarProvider` + registro `@register_provider`    │
│    · AemetMetarProvider     (code='aemet')                   │
│    · (futuros: Aviation Weather, etc.)                       │
│  Cada proveedor traduce los datos de su fuente al esquema    │
│  normalizado (provider, icao, station_code, station_name,    │
│  observation_time, temperatura, dewpoint, humidity,          │
│  wind_*, visibility_m, qnh, pressure, precipitation,         │
│  latitude, longitude, elevation, raw_metar).                 │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  CAPA 3 — Cliente HTTP                                       │
│  Clases que conocen el detalle de cada API REST              │
│    · AemetOpenDataService   (usado por AemetMetarProvider)   │
└──────────────────────────────────────────────────────────────┘
```

Para cambiar de fuente solo hace falta tocar la **capa 2** (añadir o reemplazar un `MetarProvider`); opcionalmente, si la nueva fuente requiere un cliente HTTP nuevo, se añade en la **capa 3**. La capa 1 nunca cambia.

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

### 2.4 Obtener METAR (proveedor pluggable)

Modelo: `leulit.meteo.metar`. Capa de proveedores: `MetarProvider` (interfaz) + `AemetMetarProvider` (implementación actual). Cliente HTTP: `AemetOpenDataService`.

```
[Form] provider = "aemet", icao = "LEMD"  (o station_code manual)
   │
   ▼
Usuario pulsa "Obtener observación" → action_obtener_metar()
   │
   ▼
Modelo resuelve provider a partir del campo:
   get_provider(self.provider)  → AemetMetarProvider
   │
   ▼
provider.get_observation(env, icao_code, station_code)
   │
   ▼  (dentro del proveedor AEMET)
Resolver código de estación:
   1) Dict estático ICAO_TO_IDEMA (~30 entradas)
   2) Heurística: única estación con "AEROPUERTO" en el inventario
   3) Fallback: el usuario debe introducir station_code manualmente
   │
   ▼
AemetOpenDataService → GET .../observacion/convencional/datos/estacion/{idema}
                       → GET <URL datos> (patrón 2 pasos, header api_key JWT)
   │
   ▼
Conversiones: m/s → kt (viento), km → m (visibilidad), etc.
   │
   ▼
Sintetizar texto tipo METAR + sufijo "RMK AEMET"
   │
   ▼
Provider devuelve dict normalizado al modelo
   │
   ▼
Modelo escribe los campos en el registro
```

**Importante:** AEMET OpenData **no** ofrece METAR oficiales. El proveedor `aemet` construye un texto con formato METAR a partir de la observación horaria. Se marca con `RMK AEMET` para no confundirlo con un METAR oficial.

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
- `leulit.meteo.metar` — reporte METAR independiente de proveedor (ver 2.4). Campo `provider` selecciona la fuente; hoy solo `aemet`.

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
| AEMET OpenData          | `https://opendata.aemet.es/opendata`                           | Sí (JWT)      | AEMET (España)    | Observación horaria → METAR sint.  |

Notas:

- **AEMET OpenData** usa un patrón de dos llamadas: la primera devuelve un JSON con un campo `datos` que es a su vez una URL temporal donde están los datos reales.

---

## 6. Preguntas frecuentes

**¿Por qué hay dos mapas?**
El de Leaflet sirve para que tú selecciones la ubicación (input). El iframe de Windy sirve para que veas las condiciones meteorológicas con overlay animado (output). Hacen cosas opuestas.

**¿AEMET ofrece METAR oficiales?**
No. AEMET OpenData expone observaciones horarias de estaciones convencionales. El módulo construye un texto con formato METAR a partir de esa observación y lo marca con `RMK AEMET` para distinguirlo de un METAR oficial.

**¿Necesito API key para el iframe de Windy?**
No. El embed (`embed.windy.com/embed2.html`) es público. La API key de Windy solo se requiere para la API REST (`api.windy.com/api/point-forecast/v2`).

**¿Qué pasa si AEMET no devuelve observación reciente para una estación?**
La acción `action_obtener_metar()` lanza un `UserError`. Soluciones: introducir un `station_code` distinto, probar otro aeropuerto cercano, o esperar a la siguiente actualización horaria.

**¿Cómo añado un OACI nuevo al mapping ICAO→IDEMA?**
Editar el dict `ICAO_TO_IDEMA` que usa `AemetMetarProvider` (en `models/leulit_meteo_metar_aemet.py` o el servicio de bajo nivel `models/leulit_meteo_aemet_service.py`). Alternativamente, en el formulario del registro METAR introducir el `station_code` manualmente, sin tocar el dict.

**¿Cómo cambio de proveedor de METAR?**
Selecciona otro valor en el campo **Proveedor** del registro `leulit.meteo.metar`. Para añadir un proveedor nuevo, crea una subclase de `MetarProvider` decorada con `@register_provider` e impórtala en `models/__init__.py`. El modelo, las vistas y el menú no necesitan cambios: el nuevo `code` aparece automáticamente en el selector.
