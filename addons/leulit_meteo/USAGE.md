# Guía de Uso — Leulit Meteo

Manual práctico de uso del módulo `leulit_meteo`. Para instalación consulta `INSTALL.md`; para una visión general del módulo, `README.md`; para flujos completos, `WORKFLOW.md`.

## Contenidos

1. [Consultar clima en un punto](#1-consultar-clima-en-un-punto)
2. [Consultar clima en una ruta (polilínea)](#2-consultar-clima-en-una-ruta-polilínea)
3. [Plantillas de rutas](#3-plantillas-de-rutas)
4. [Reportes METAR](#4-reportes-metar)
5. [Añadir un nuevo proveedor](#5-añadir-un-nuevo-proveedor)
6. [Filtros y búsquedas habituales](#6-filtros-y-búsquedas-habituales)
7. [Integración programática](#7-integración-programática)
8. [Casos de uso prácticos](#8-casos-de-uso-prácticos)
9. [Mejores prácticas](#9-mejores-prácticas)

---

## 1. Consultar clima en un punto

Menú: **Meteorología → Consultas**.

1. Pulsa **Crear**.
2. Rellena **Ubicación** (descriptiva), **Latitud** y **Longitud**.
3. Selecciona **Fuente de datos**: `Open-Meteo` (sin API key) o `Windy` (requiere API key configurada).
4. Pulsa el botón correspondiente:
   - **Consultar clima actual** — usa Open-Meteo y rellena temperatura, humedad, viento, descripción y código de clima.
   - **Obtener pronóstico** — pronóstico Open-Meteo a varios días.
   - **Consultar Windy** — usa el modelo Windy seleccionado en **Meteorología → Configuración** (GFS, ECMWF, ICON, ICON-EU o NAM).

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
4. Pulsa **Obtener observación** (`action_obtener_metar`). El sistema resuelve automáticamente la estación interna del proveedor (en AEMET, el IDEMA) y descarga la última observación.

No es necesario tocar el código de estación: es un identificador interno del proveedor y aparece read-only en la pestaña **Información técnica** del formulario, junto con coordenadas y elevación.

El registro se rellena con: `station_name`, `observation_time`, `temperatura`, `dewpoint`, `humidity`, `wind_direction`, `wind_speed_kt`, `wind_gust_kt`, `visibility_m`, `qnh`, `pressure`, `precipitation`, `latitud`, `longitud`, `elevation`, `edad_datos_minutos`, `estado_datos` y un `raw_metar`.

**Importante — limitaciones del proveedor AEMET**:

- AEMET OpenData **no publica METAR oficiales**. El campo `raw_metar` es una cadena tipo METAR construida a partir de la observación horaria, etiquetada con `RMK AEMET`.
- La resolución OACI → IDEMA usa un mapeo estático con ~30 aeropuertos/aeródromos habituales (LEMD, LEBL, LELL, LEMG, LEAL, LEVC, LEZL, LEBB, LEPA, LEIB, LEMH, GCLP, GCXO, GCTS, LECU, LETO, …). Si el OACI no está en el dict, el proveedor consulta el inventario AEMET para localizarlo por nombre. Si aun así no se resuelve, usa el botón **Buscar estación AEMET** para seleccionarla manualmente.
- Requiere `leulit_meteo.aemet_api_key` configurado en parámetros del sistema.

## 5. Añadir un nuevo proveedor

Crear una subclase de `MetarProvider` decorada con `@register_provider` y registrarla en `models/__init__.py`. El modelo, las vistas y el menú no necesitan cambios; el nuevo `code` aparece automáticamente en el selector `provider`.

```python
# models/leulit_meteo_metar_aviationweather.py
from .leulit_meteo_metar_provider import MetarProvider, register_provider

@register_provider
class AviationWeatherMetarProvider(MetarProvider):
    code = 'aviationweather'
    label = 'Aviation Weather (NOAA)'

    def get_observation(self, env, icao_code=None, station_code=None):
        # Llamar a la API y devolver el dict normalizado:
        # provider, icao, station_code, station_name, observation_time,
        # temperatura, dewpoint, humidity, wind_direction, wind_speed_kt,
        # wind_gust_kt, visibility_m, qnh, pressure, precipitation,
        # latitude, longitude, elevation, raw_metar
        ...
```

Métodos opcionales: `validate(env)`, `prefill_station_code(icao_code)`, `resolve(env, icao_code)`, `coverage(icao_code)`.

`resolve(env, icao_code)` se invoca antes de `get_observation` cuando el usuario solo informó el OACI; por defecto delega en `prefill_station_code` (mapa estático), pero un proveedor puede sobrescribirlo para consultar un inventario remoto. El modelo cachea el resultado en `station_code` para futuras consultas.

## 6. Filtros y búsquedas habituales

**En `leulit.meteo.metar`**:

- Filtros: *Datos actuales*, *Datos recientes*, *Datos antiguos* (sobre `estado_datos`), *Mis consultas* (`user_id=uid`).
- Agrupar por: **Proveedor**, **OACI**, **Código de estación**, **Usuario**.

**En `leulit.meteo.consulta`**:

- Filtros y agrupaciones por fuente de datos, ubicación, fecha y usuario disponibles en la vista de búsqueda.

## 7. Integración programática

### 7.1. Consulta de clima genérico

Método de clase reutilizable en `leulit.meteo.consulta`:

```python
result = self.env['leulit.meteo.consulta'].consultar_clima_ubicacion(
    ubicacion='Aeródromo Sabadell',
    latitud=41.5208,
    longitud=2.1050,
)
# result -> {'consulta_id', 'temperatura', 'viento', 'humedad', 'descripcion'}
```

### 7.2. METAR vía proveedor

```python
data = self.env['leulit.meteo.metar'].obtener_metar(
    icao_code='LEMD',
    provider='aemet',
)
# data -> {'provider', 'icao', 'station_code', 'station_name',
#          'observation_time', 'temperatura', 'dewpoint', 'humidity',
#          'wind_speed_kt', 'wind_gust_kt', 'wind_direction',
#          'visibility_m', 'qnh', 'raw_metar', ...}
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

Si solo conoces el código de estación:

```python
data = self.env['leulit.meteo.metar'].obtener_metar(
    station_code='0076',
    provider='aemet',
)
```

### 7.3. Acceso directo a los servicios (sin pasar por modelos)

```python
from odoo.addons.leulit_meteo.models.leulit_meteo_service import OpenMeteoService
from odoo.addons.leulit_meteo.models.leulit_meteo_aemet_service import AemetOpenDataService

# Open-Meteo (no requiere API key)
current = OpenMeteoService.get_current_weather(latitude=40.4165, longitude=-3.7026)
forecast = OpenMeteoService.get_forecast(latitude=40.4165, longitude=-3.7026, days=3)

# AEMET (requiere api_key)
api_key = self.env['ir.config_parameter'].sudo().get_param('leulit_meteo.aemet_api_key')
metar_like = AemetOpenDataService.get_metar_like(api_key=api_key, icao_code='LEMG')
```

## 8. Casos de uso prácticos

### 8.1. Vincular METAR a un vuelo

```python
class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'

    metar_id = fields.Many2one('leulit.meteo.metar')

    def action_obtener_meteo_salida(self):
        for vuelo in self:
            aerodromo = vuelo.aerodromo_salida_id
            if aerodromo and aerodromo.codigo_oaci:
                data = self.env['leulit.meteo.metar'].obtener_metar(
                    icao_code=aerodromo.codigo_oaci,
                    provider='aemet',
                    persistir=True,
                )
                if data and data.get('record_id'):
                    vuelo.metar_id = data['record_id']
```

### 8.2. Validar condiciones antes de volar

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

## 9. Mejores prácticas

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

- **Manejar `None`**: cualquier llamada puede devolver `None` por fallo de red, API key inválida o estación sin observación reciente. Comprueba siempre el resultado antes de acceder a sus claves.
- **Logging**: usa `_logger` (`logging.getLogger(__name__)`) para registrar errores y respuestas inesperadas; no silencies excepciones.
- **API keys**: lee siempre desde `ir.config_parameter` (`leulit_meteo.aemet_api_key`, equivalente para Windy), nunca las hardcodees.
- **AEMET ≠ METAR oficial**: si necesitas METAR aeronáuticos certificados, consulta el proveedor oficial correspondiente; el `raw_metar` de este módulo es sintético.

---

Ver también: [README.md](README.md) · [WORKFLOW.md](WORKFLOW.md)
