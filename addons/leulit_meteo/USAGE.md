# Guía de Uso — Leulit Meteo

Manual práctico de uso del módulo `leulit_meteo`. Para instalación consulta `INSTALL.md`; para una visión general del módulo, `README.md`; para flujos completos, `WORKFLOW.md`.

## Contenidos

1. [Consultar clima en un punto](#1-consultar-clima-en-un-punto)
2. [Consultar clima en una ruta (polilínea)](#2-consultar-clima-en-una-ruta-polilínea)
3. [Plantillas de rutas](#3-plantillas-de-rutas)
4. [Reportes METAR](#4-reportes-metar)
5. [Aeródromos de Referencia y auto-resolución](#5-aeródromos-de-referencia-y-auto-resolución)
6. [Histórico automático de METAR](#6-histórico-automático-de-metar)
7. [Sincronización de aeródromos desde aviationweather.gov](#7-sincronización-de-aeródromos-desde-aviationweathergov)
8. [Añadir un nuevo proveedor](#8-añadir-un-nuevo-proveedor)
9. [Filtros y búsquedas habituales](#9-filtros-y-búsquedas-habituales)
10. [Integración programática](#10-integración-programática)
11. [Casos de uso prácticos](#11-casos-de-uso-prácticos)
12. [Mejores prácticas](#12-mejores-prácticas)

---

## 1. Consultar clima en un punto

Menú: **Meteorología → Consultas**.

1. Pulsa **Crear**.
2. Rellena **Ubicación** (descriptiva), **Latitud** y **Longitud**.
3. Selecciona **Fuente de datos**: `Open-Meteo` (sin API key) o `Windy` (requiere API key configurada).
4. Pulsa el botón correspondiente:
   - **Consultar clima actual** — usa Open-Meteo y rellena temperatura, humedad, viento, descripción y código de clima.
   - **Obtener pronóstico** — pronóstico Open-Meteo a varios días.
   - **Consultar Windy** — usa el modelo Windy seleccionado en **Meteorología → Configuración → API Keys** (GFS, ECMWF, ICON, ICON-EU o NAM).

Los campos `temperatura`, `humedad`, `velocidad_viento`, `descripcion_clima` y `codigo_clima` se actualizan tras la consulta.

## 2. Consultar clima en una ruta (polilínea)

1. En la ficha de **Consulta**, marca el flag **Es polilínea**.
2. Añade los puntos en la pestaña **Puntos de la ruta** (`puntos_ids`): cada punto con su latitud y longitud.
3. Pulsa **Consultar Windy** — la consulta se hace para cada punto de la ruta y se guardan los resultados por waypoint.

El comportamiento de `action_consultar_windy()` cambia automáticamente según `es_polilinea`: punto único o polilínea.

## 3. Plantillas de rutas

Permiten reutilizar rutas frecuentes (ej. tramos habituales de instrucción o vuelos comerciales recurrentes).

**Guardar una ruta como plantilla**:

1. Crea una consulta polilínea con todos sus puntos.
2. Pulsa **Guardar como plantilla** (`action_guardar_como_template`).

**Cargar una plantilla en una consulta nueva**:

1. En la consulta, selecciona **Plantilla de ruta** (`ruta_template_id`).
2. Pulsa **Cargar ruta desde plantilla** (`action_cargar_ruta_template`) — los waypoints se insertan en `puntos_ids`.

## 4. Reportes METAR

Menú: **Meteorología → Reportes METAR**. Modelo `leulit.meteo.metar` con arquitectura de proveedores: el campo `provider` selecciona la fuente concreta (hoy solo `aemet`).

1. **Crear** un nuevo registro `leulit.meteo.metar`.
2. Selecciona el **Proveedor** (por defecto `AEMET (España)`).
3. Escribe un **OACI** (4 letras, ej. `LEMD`, `LELL`, `GCLP`).
4. Pulsa **Obtener briefing** (`action_obtener_briefing`).

El sistema consulta la tabla **Aeródromos de Referencia** para determinar la FIR. Si el OACI no está registrado, lo **auto-resuelve** consultando OpenAIP y CheckWX (ver sección 5).

El registro se rellena con:
- **RAW intacto**: `raw_metar`, `raw_taf`, `raw_sigmet` — texto oficial de AEMET, sin modificar.
- **Campos decodificados** (best-effort): `observation_time`, `temperatura`, `dewpoint`, `wind_direction`, `wind_speed_kt`, `wind_gust_kt`, `visibility_m`, `qnh`, `edad_datos_minutos`, `estado_datos`.
- **Metadatos de resolución**: `fir_code`, `usa_referencia`, `ref_icao`, `ref_nombre`, `station_name`.

Si el OACI es un helipuerto sin METAR propio y está dado de alta con `tiene_metar_propio = False` en **Aeródromos de Referencia**, se muestra un aviso informativo indicando el aeródromo de referencia usado.

**Notas del proveedor AEMET**:

- Los campos `raw_metar`, `raw_taf` y `raw_sigmet` contienen el texto oficial publicado por AEMET OpenData, **sin alterar** (válido a efectos legales/AESA).
- El SIGMET se obtiene por FIR (LECM/LECB/GCCC); si el OACI no está en la tabla de referencia, el SIGMET no estará disponible.
- Requiere `leulit_meteo.aemet_api_key` configurado en parámetros del sistema.

## 5. Aeródromos de Referencia y auto-resolución

Menú: **Meteorología → Aeródromos de Referencia** (solo administradores). Modelo `leulit.meteo.icao.reference`.

Cada registro mapea un OACI a su FIR y, opcionalmente, al aeródromo cercano que emite METAR cuando el punto no tiene servicio MET propio (helipuertos).

**Campos principales**:

| Campo | Descripción |
|-------|-------------|
| `icao` | Código OACI (4 letras) |
| `fir` | FIR asignada: LECM, LECB o GCCC |
| `tiene_metar_propio` | Si está desmarcado, se usa `ref_icao` para METAR/TAF |
| `ref_icao` | OACI del aeródromo con METAR al que redirigir |
| `proveedor_oficial` | Fuente METAR: AEMET, CheckWX o Ninguno |
| `latitud` / `longitud` | Coordenadas (rellenadas en auto-resolución) |
| `station_code` | Código de estación AEMET para METAR sintético |
| `auto_resolved` | `True` si el sistema lo creó automáticamente |
| `proxima_actualizacion` | Momento esperado del siguiente METAR (usado por el cron) |

**Auto-resolución de OACIs desconocidos**:

Cuando se pide un briefing para un OACI que no está en la tabla, el sistema ejecuta `_auto_resolve()` automáticamente:

1. Consulta **OpenAIP** para obtener coordenadas y nombre oficial.
2. Consulta **CheckWX** para verificar si el OACI tiene METAR propio.
3. Si no tiene METAR propio, busca el aeródromo con METAR más cercano en un radio de 150 km.
4. Asigna la FIR por heurística de coordenadas (lat ≤ 30 → GCCC; lon ≥ -1.5 y lat ≥ 40 → LECB; resto → LECM).
5. Busca la estación AEMET más próxima (para METAR sintético).
6. Crea el registro en la tabla con `auto_resolved = True`.

Los registros auto-resueltos aparecen atenuados en la lista. Puedes editarlos manualmente para corregir o ampliar la información.

**Añadir un aeródromo manualmente**:

Ir a **Meteorología → Aeródromos de Referencia** y crear un registro. Indicar FIR (LECM/LECB/GCCC) y, si el punto no emite METAR propio, desmarcar `tiene_metar_propio` y rellenar `ref_icao` con el OACI del aeródromo cercano. No hay que tocar ningún fichero Python.

## 6. Histórico automático de METAR

El cron `cron_actualizar_metar_referencia` se ejecuta cada 10 minutos y descarga METAR/TAF de todos los aeródromos de referencia que tienen la `proxima_actualizacion` vencida (o nula). Los datos se almacenan en `leulit.meteo.historico`.

**Lógica del cron**:

- Solo procesa aeródromos cuya `proxima_actualizacion` es `False` o ha pasado.
- Si el METAR no ha cambiado (mismo `observation_time` que el último registro), pospone la siguiente comprobación 35 min.
- Si el METAR es nuevo, crea un registro en `leulit.meteo.historico` y programa la siguiente actualización a `observation_time + 35 min`.
- Si hay errores, envía un email al `leulit_meteo.email_errores` configurado (si lo hay).

**Activar/desactivar el cron**: **Meteorología → Configuración → Parámetros**, campo **Actualización automática de METAR activa**.

**Ver el histórico de un aeródromo**: en la ficha del aeródromo de referencia, pulsar el botón estadístico **Histórico** (muestra el recuento y abre la lista de registros).

**Campos del histórico (`leulit.meteo.historico`)**:

| Campo | Descripción |
|-------|-------------|
| `icao_reference_id` | Aeródromo de referencia |
| `icao_consultar` | OACI realmente consultado (puede diferir si usa referencia) |
| `raw_metar` / `raw_taf` / `raw_sigmet` | Textos oficiales sin alterar |
| `observation_time` | Hora UTC de la observación METAR |
| `fecha_obtencion` | Momento en que el cron lo descargó |
| `fuente_metar` / `fuente_taf` | Proveedor que entregó el dato (aemet, checkwx, ninguno) |
| `usa_referencia` | `True` si los datos vienen del `ref_icao` |

## 7. Sincronización de aeródromos desde aviationweather.gov

En **Meteorología → Configuración → Parámetros**, pulsar el botón **Actualizar aeródromos de referencia**. **No requiere API key.**

El proceso:

1. Consulta aviationweather.gov (NOAA/FAA) para obtener todas las estaciones LE* y GC* que declaran capacidad METAR o TAF. Usa primero el endpoint ADDS clásico (XML con `site_type`) y, si falla, cae al API nuevo con bounding box sobre Península y Canarias.
2. Filtra solo aeródromos con prefijo LE* (España peninsular + Baleares) o GC* (Canarias) que tengan `<METAR>` o `<TAF>` en su `site_type`.
3. **Crea** registros nuevos con `tiene_metar_propio = True` y `proxima_actualizacion = None` (el cron los procesará en su siguiente ejecución).
4. **Actualiza** nombre y coordenadas de los ya existentes con `tiene_metar_propio = True`.
5. **No toca** registros con `tiene_metar_propio = False` (helipuertos y refs manuales).
6. **Elimina** los registros con `tiene_metar_propio = True` que ya no aparecen en la fuente.

Resultado: la notificación muestra el número de aeródromos añadidos, actualizados y eliminados.

## 8. Añadir un nuevo proveedor

Crear una subclase de `MetarProvider` decorada con `@register_provider` y registrarla en `models/__init__.py`. El modelo, las vistas y el menú no necesitan cambios; el nuevo `code` aparece automáticamente en el selector `provider`.

```python
# models/leulit_meteo_metar_aviationweather.py
from .leulit_meteo_metar_provider import MetarProvider, register_provider

@register_provider
class AviationWeatherMetarProvider(MetarProvider):
    code = 'aviationweather'
    label = 'Aviation Weather (NOAA)'

    def get_observation(self, env, icao_code=None, station_code=None):
        # Devolver el dict normalizado (ver leulit_meteo_metar_provider.py):
        # provider, icao, icao_consultar, usa_referencia, ref_icao, ref_nombre,
        # fir_code, station_code, station_name,
        # raw_metar, raw_taf, raw_sigmet,
        # observation_time, temperatura, dewpoint, wind_direction, wind_speed_kt,
        # wind_gust_kt, visibility_m, qnh,
        # humidity, pressure, precipitation, latitude, longitude, elevation
        ...
```

Método opcional: `validate(env)` — comprueba que el proveedor está bien configurado (API key, etc.).

## 9. Filtros y búsquedas habituales

**En `leulit.meteo.metar`**:

- Filtros: *Datos actuales*, *Datos recientes*, *Datos antiguos* (sobre `estado_datos`), *Usa referencia*, *Mis consultas* (`user_id=uid`).
- Agrupar por: **Proveedor**, **OACI**, **FIR**, **Usuario**.

**En `leulit.meteo.icao.reference`**:

- Filtros: *Con METAR propio*, *Usa referencia*, *Auto-resueltos*.
- Filtros por FIR: *FIR Madrid (LECM)*, *FIR Barcelona (LECB)*, *FIR Canarias (GCCC)*.
- Agrupar por: **FIR**, **Tiene METAR propio**, **Proveedor**.

**En `leulit.meteo.consulta`**:

- Filtros y agrupaciones por fuente de datos, ubicación, fecha y usuario disponibles en la vista de búsqueda.

## 10. Integración programática

### 10.1. Consulta de clima genérico

Método de clase reutilizable en `leulit.meteo.consulta`:

```python
result = self.env['leulit.meteo.consulta'].consultar_clima_ubicacion(
    ubicacion='Aeródromo Sabadell',
    latitud=41.5208,
    longitud=2.1050,
)
# result -> {'consulta_id', 'temperatura', 'viento', 'humedad', 'descripcion'}
```

### 10.2. METAR vía proveedor

```python
data = self.env['leulit.meteo.metar'].obtener_metar(
    icao_code='LEMD',
    provider='aemet',
)
# data -> {'provider', 'icao', 'icao_consultar', 'usa_referencia',
#          'ref_icao', 'ref_nombre', 'fir_code', 'station_name',
#          'raw_metar', 'raw_taf', 'raw_sigmet',
#          'observation_time', 'temperatura', 'dewpoint',
#          'wind_speed_kt', 'wind_gust_kt', 'wind_direction',
#          'visibility_m', 'qnh', ...}
```

Para persistir el resultado como registro:

```python
data = self.env['leulit.meteo.metar'].obtener_metar(
    icao_code='LEBL',
    provider='aemet',
    persistir=True,
)
record = self.env['leulit.meteo.metar'].browse(data['record_id'])
```

### 10.3. Briefing simplificado con histórico (`briefing_oaci`)

```python
result = self.env['leulit.meteo.metar'].briefing_oaci('LEUL')
# result -> {'record_id', 'raw_metar', 'raw_taf', 'raw_metar_est',
#            'historico', 'observation_time', 'provider',
#            'metar_icao', 'usa_referencia'}
# → None si no hay datos disponibles
```

Con modo histórico (solo consulta BD, no llama a la API):

```python
from datetime import datetime
result = self.env['leulit.meteo.metar'].briefing_oaci(
    'LEUL', fecha=datetime(2026, 4, 27, 14, 30))
```

Ver [INTEGRACION_VUELO.md](INTEGRACION_VUELO.md) para la documentación completa de `briefing_oaci`.

### 10.4. Acceso directo a los servicios

```python
from odoo.addons.leulit_meteo.models.leulit_meteo_service import OpenMeteoService
from odoo.addons.leulit_meteo.models.leulit_meteo_aemet_service import AemetOpenDataService
from odoo.addons.leulit_meteo.models.leulit_meteo_checkwx_service import CheckWXService
from odoo.addons.leulit_meteo.models.leulit_meteo_openaip_service import OpenAIPService

# Open-Meteo (no requiere API key)
current = OpenMeteoService.get_current_weather(latitude=40.4165, longitude=-3.7026)
forecast = OpenMeteoService.get_forecast(latitude=40.4165, longitude=-3.7026, days=3)

# AEMET — mensajes oficiales por OACI o FIR
api_key = self.env['ir.config_parameter'].sudo().get_param('leulit_meteo.aemet_api_key')
raw_metar = AemetOpenDataService.get_message('METAR', 'LEMG', api_key)
raw_taf   = AemetOpenDataService.get_message('TAF',   'LEMG', api_key)
raw_sigmet = AemetOpenDataService.get_message('SIGMET', 'LECM', api_key)

# CheckWX — METAR internacional + aeródromo más cercano
checkwx_key = self.env['ir.config_parameter'].sudo().get_param('leulit_meteo.checkwx_api_key')
metar = CheckWXService.get_metar('EGLL', checkwx_key)
nearest = CheckWXService.get_nearest_metar(40.0, -3.7, 400, checkwx_key)  # radio en nm

# OpenAIP — coordenadas de un OACI
openaip_key = self.env['ir.config_parameter'].sudo().get_param('leulit_meteo.openaip_api_key')
info = OpenAIPService.get_airport_by_icao('LEUL', openaip_key)
# info -> {'lat', 'lon', 'name', ...} o None
```

## 11. Casos de uso prácticos

### 11.1. Vincular METAR a un vuelo

```python
class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'

    metar_id = fields.Many2one('leulit.meteo.metar')

    def action_obtener_meteo_salida(self):
        for vuelo in self:
            if vuelo.aerodromo_salida_id and vuelo.aerodromo_salida_id.codigo_oaci:
                data = self.env['leulit.meteo.metar'].obtener_metar(
                    icao_code=vuelo.aerodromo_salida_id.codigo_oaci,
                    provider='aemet',
                    persistir=True,
                )
                if data and data.get('record_id'):
                    vuelo.metar_id = data['record_id']
```

### 11.2. Validar condiciones antes de volar

```python
def comprobar_condiciones(self):
    self.ensure_one()
    data = self.env['leulit.meteo.metar'].obtener_metar(
        icao_code=self.aerodromo_id.codigo_oaci,
        provider='aemet',
    )
    if not data:
        return False  # sin observación reciente

    viento = data.get('wind_speed_kt') or 0
    rachas = data.get('wind_gust_kt') or 0
    visibilidad = data.get('visibility_m') or 0

    return viento <= 25 and rachas <= 35 and visibilidad >= 5000
```

Para puntos sin estación AEMET (ruta libre, escuela en zona rural) usa `consultar_clima_ubicacion` con coordenadas y aplica los mismos umbrales sobre `viento` y `descripcion`.

## 12. Mejores prácticas

- **Validar coordenadas** con `@api.constrains` antes de llamar a los servicios:

  ```python
  @api.constrains('latitud', 'longitud')
  def _check_coordenadas(self):
      for rec in self:
          if not -90 <= rec.latitud <= 90:
              raise ValidationError("Latitud fuera de rango (-90..90).")
          if not -180 <= rec.longitud <= 180:
              raise ValidationError("Longitud fuera de rango (-180..180).")
  ```

- **Manejar `None`**: cualquier llamada puede devolver `None` por fallo de red, API key inválida o aeródromo sin publicación activa. Comprueba siempre el resultado antes de acceder a sus claves.
- **Logging**: usa `_logger` (`logging.getLogger(__name__)`) para registrar errores y respuestas inesperadas; no silencies excepciones.
- **API keys**: lee siempre desde `ir.config_parameter` (`leulit_meteo.aemet_api_key`, `leulit_meteo.checkwx_api_key`, `leulit_meteo.openaip_api_key`, `leulit_meteo.windy_api_key`), nunca las hardcodees.
- **RAW prevalece**: los campos decodificados (`temperatura`, `wind_speed_kt`, etc.) son auxiliares; ante cualquier duda, el texto `raw_metar` / `raw_taf` / `raw_sigmet` es la fuente de verdad (válido a efectos legales/AESA).
- **Aeródromos de Referencia**: para que un helipuerto obtenga METAR y SIGMET, debe estar dado de alta en `leulit.meteo.icao.reference` con su FIR correcta y, si no emite METAR propio, con un `ref_icao` al aeródromo cercano. Si no está dado de alta, el sistema intentará auto-resolverlo (necesita OpenAIP y/o CheckWX key).

---

Ver también: [README.md](README.md) · [WORKFLOW.md](WORKFLOW.md) · [INTEGRACION_VUELO.md](INTEGRACION_VUELO.md)
