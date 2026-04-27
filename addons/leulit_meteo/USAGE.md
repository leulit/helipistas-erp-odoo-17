# Guía de Uso - Leulit Meteorología

## Tabla de Contenidos

1. [Inicio Rápido](#inicio-rápido)
2. [Configuración](#configuración)
3. [Widget de Mapa Interactivo](#widget-de-mapa-interactivo)
4. [Consultas con Windy API](#consultas-con-windy-api)
5. [Polilíneas y Rutas](#polilíneas-y-rutas)
6. [Consultas Manuales](#consultas-manuales)
7. [Integración Programática](#integración-programática)
8. [Casos de Uso Comunes](#casos-de-uso-comunes)
9. [Mejores Prácticas](#mejores-prácticas)

---

## Inicio Rápido

### Primera Consulta en 5 Pasos

1. **Acceder al módulo**
   ```
   Navegación → Meteorología → Consultas
   ```

2. **Crear nueva consulta**
   - Clic en botón "Crear"

3. **Completar datos de ubicación**
   ```
   Ubicación: Madrid - Cuatro Vientos
   Latitud: 40.3717
   Longitud: -3.7856
   ```

4. **Obtener datos**
   - Clic en "Consultar Clima Actual"

5. **Ver resultados**
   - Los campos se rellenan automáticamente con los datos meteorológicos

---

## Configuración

### Configurar Windy API (Recomendado)

Para acceder a modelos meteorológicos avanzados (GFS, ECMWF), configure Windy:

1. **Obtener API Key**
   - Visitar https://api.windy.com/keys
   - Registrarse (gratuito)
   - Copiar la API Key

2. **Configurar en Odoo**
   ```
   Navegación → Ajustes → Meteorología
   ```
   - Pegar la API Key en el campo "Windy API Key"
   - Seleccionar modelo por defecto (GFS recomendado)
   - Clic en "Validar API Key" para verificar

3. **Modelos Disponibles**
   - **GFS**: Global Forecast System (16 días, actualización cada 6h)
   - **ECMWF**: European Centre (más preciso, 10 días)
   - **ICON**: DWD alemán (7 días)
   - **ICON-EU**: Europea de alta resolución (5 días)
   - **NAM**: North American Model (3 días)

---

## Widget de Mapa Interactivo

### Uso Básico del Mapa

El widget de mapa interactivo permite seleccionar ubicaciones visualmente:

**Características:**
- 🗺️ Mapa interactivo con OpenStreetMap
- 📍 Click para establecer ubicación
- 🖱️ Arrastrar markers para mover
- 🔍 Zoom y navegación
- 📐 Modos: Punto único o Polilínea (ruta)

### Modo Punto Único

**Uso:**
1. Crear nueva consulta
2. En el mapa, click en la ubicación deseada
3. Las coordenadas se actualizan automáticamente
4. Arrastra el marker para ajustar
5. Click en "Consultar" para obtener datos

**Controles:**
- **Centrar**: Centra el mapa en tu ubicación actual
- **Limpiar**: Elimina el marker actual
- **Pantalla completa**: Amplía el mapa (navegadores compatibles)

### Modo Polilínea (Ruta)

Ideal para planificación de rutas de vuelo:

**Activar modo ruta:**
1. En la consulta, marcar checkbox "¿Es Polilínea?"
2. O clic en botón "Modo: Ruta" en la barra del mapa

**Agregar puntos:**
1. Click en el mapa para agregar puntos secuencialmente
2. Cada click agrega un nuevo waypoint
3. Los puntos se numeran automáticamente
4. Se dibuja una línea conectando los puntos

**Gestionar puntos:**
- **Mover**: Arrastra un marker para reposicionarlo
- **Eliminar**: Click derecho en un marker
- **Reordenar**: Edita en la pestaña "Puntos de Ruta"

**Guardar ruta:**
1. Click en "Guardar Ruta" en la barra del mapa
2. Los puntos se guardan en la base de datos
3. Puedes editar nombre/altitud de cada punto

---

## Consultas con Windy API

### Datos de Windy: Cómo se Obtienen y Muestran

**Importante**: Windy tiene **dos componentes separados**:

#### 1. **Windy API REST** (Datos Numéricos)
- Llamas a `https://api.windy.com/api/point-forecast/v2`
- Obtienes JSON con temperatura, viento, presión, etc.
- **Requiere API Key**
- Los valores se guardan en la base de datos
- Se muestran en la pestaña "Puntos de Ruta" (tabla)

#### 2. **Windy Embed** (Visualización)
- Iframe con `https://embed.windy.com/embed2.html`
- Overlay meteorológico animado (viento, nubes, temperatura)
- **NO requiere API Key** (embed público)
- Se muestra en la pestaña "Mapa Windy Visual"
- Es solo visualización (no se obtienen datos del iframe)

### Consulta Simple con Windy

**Requisito:** API Key de Windy configurada

**Pasos:**
1. Crear consulta meteorológica
2. Seleccionar "Fuente de Datos: Windy"
3. Establecer ubicación (mapa o coordenadas)
4. Click en "Consultar Windy"

**Datos obtenidos:**
- Temperatura (°C)
- Punto de rocío
- Humedad relativa (%)
- Presión atmosférica (hPa)
- Cobertura de nubes (%)
- Precipitación (mm)
- Viento: velocidad, dirección, rachas
- Modelo utilizado (GFS, ECMWF, etc.)

**Ventajas de Windy vs Open-Meteo:**
- ✅ Múltiples modelos meteorológicos profesionales
- ✅ Mayor precisión en vientos
- ✅ Datos de presión atmosférica
- ✅ Punto de rocío
- ⚠️ Requiere API Key
- ⚠️ Límite de consultas (depende del plan)

---

## Polilíneas y Rutas

### ¿Qué es una Polilínea en este Contexto?

Una **polilínea** es una **ruta de vuelo** definida por múltiples waypoints (puntos).
Por ejemplo: LEMD → Waypoint1 → Waypoint2 → LEBL

**Casos de uso**:
- Planificar vuelo cross-country
- Patrulla de vigilancia
- Ruta comercial frecuente

### Selector de Rutas: Cómo Funciona

El módulo incluye un **sistema de plantillas de rutas** para reutilizar:

**Crear Plantilla**:
1. Ir a Meteorología → Rutas Predefinidas
2. Crear nueva ruta: nombre "LEMD-LEBL"
3. Agregar waypoints con coordenadas
4. Guardar

**Usar Plantilla en Consulta**:
1. Nueva consulta meteorológica
2. Campo "Cargar Ruta Predefinida" → seleccionar "LEMD-LEBL"
3. Los puntos se cargan automáticamente
4. También puedes usar `@onchange` automático al seleccionar

**Guardar Consulta Actual como Plantilla**:
1. Después de crear una ruta manualmente en el mapa
2. Click botón "Guardar como Plantilla"

**En Tabla "Puntos de Ruta"**:
- Cada fila = 1 waypoint con sus datos meteorológicos
- Temperatura por punto para calcular densidad de aire
- Viento en ruta para estimar derive y tiempo
- Cobertura de nubes para decisión VFR/IFR
- Precipitación para evitar zonas peligrosas

**En "Resumen de Condiciones"** (campos computados):
- Temperatura Mínima/Máxima: rango térmico en toda la ruta
- Viento Máximo: peor condición de viento esperada
- Condiciones Críticas: ⚠️ alerta si viento > 50 km/h o temp < 0°C

**En "Mapa Windy Visual"** (pestaña):
- Iframe embebido que muestra overlay meteorológico animado
- Cambia capas con controles de Windy (viento, temperatura, nubes)
- Útil para ver patterns generales y evolución temporal
- NO extrae datos (solo visualización)

### Visualización de Datos de Windy

Una vez consultada la API, los datos se muestran en **3 lugares**:

#### 1. Pestaña "Mapa Windy Visual"
```
┌────────────────────────────────────────┐
│  [Iframe de Windy Embed]              │
│                                        │
│  🗺️ Mapa animado con overlay         │
│  🌬️ Viento visible en movimiento     │
│  🌡️ Cambiar a capa temperatura        │
│  ☁️ Cambiar a capa nubes              │
│  ⏱️ Timeline para ver evolución       │
│                                        │
└────────────────────────────────────────┘
```
**NO requiere API Key** - es visualización pública

#### 2. Pestaña "Puntos de Ruta"
```
| # | Nombre    | Lat    | Lon    | Temp | Viento | Nubes |
|---|-----------|--------|--------|------|--------|-------|
| 1 | LEMD      | 40.47  | -3.56  | 18°C | 15km/h | 30%   |
| 2 | Waypoint1 | 40.85  | -2.45  | 17°C | 20km/h | 45%   |
| 3 | Waypoint2 | 41.23  | -1.12  | 16°C | 18km/h | 35%   |
| 4 | LEBL      | 41.30  | 2.08   | 19°C | 12km/h | 20%   |
```
**Datos numéricos de la API REST** - requiere API Key

#### 3. Resumen de Condiciones
```
Temperatura Mínima: 16°C
Temperatura Máxima: 19°C
Viento Máximo: 20 km/h
⚠️ Condiciones Críticas: No
```
**Calculado** desde los datos de los punto
Ejemplo: Vuelo Madrid (LEMD) → Barcelona (LEBL)

**Paso 1: Crear ruta**
1. Nueva consulta meteorológica
2. Nombre: "Ruta LEMD-LEBL"
3. Marcar "¿Es Polilínea?"
4. Fuente de datos: "Windy"

**Paso 2: Definir waypoints**
En el mapa, click en:
1. Madrid-Barajas (40.4936, -3.5668)
2. Calatayud (41.3561, -1.6408)
3. Lleida (41.6168, 0.6208)
4. Barcelona-El Prat (41.2974, 2.0833)

**Paso 3: Ajustar puntos**
En pestaña "Puntos de Ruta":
- Renombrar: "LEMD", "Waypoint 1", "Waypoint 2", "LEBL"
- Agregar altitud si es relevante
- Reordenar arrastrando el handle

**Paso 4: Obtener meteorología**
1. Click en "Consultar Windy"
2. Esperar (puede tardar según número de puntos)
3. Ver datos en cada punto de la tabla

**Interpretar resultados:**
- Temperatura por punto para calcular densidad de aire
- Viento en ruta para estimar derive y tiempo
- Cobertura de nubes para decisión VFR/IFR
- Precipitación para evitar zonas peligrosas

---

## Consultas Manuales

### Consultar Clima Actual

El clima actual incluye:
- Temperatura y sensación térmica
- Humedad relativa
- Precipitación actual
- Velocidad y dirección del viento
- Rachas de viento
- Cobertura de nubes
- Descripción de condiciones

**Pasos:**
1. Crear o abrir consulta existente
2. Verificar coordenadas
3. Clic en "Consultar Clima Actual"
4. Los datos se actualizan automáticamente

### Obtener Pronóstico

El pronóstico incluye datos agregados diarios hasta 16 días:
- Temperaturas máximas y mínimas
- Precipitación acumulada
- Velocidad máxima de viento
- Dirección predominante del viento

**Pasos:**
1. Crear o abrir consulta
2. Clic en "Obtener Pronóstico"
3. Los datos JSON se almacenan en la pestaña "Pronóstico"

### Obtener Reporte METAR

Los METAR son reportes meteorológicos aeronáuticos oficiales:
- Reporte completo en formato texto estándar
- Datos decodificados automáticamente
- Categoría de vuelo (VFR/MVFR/IFR/LIFR)
- Información de viento, visibilidad, nubes, QNH

**Pasos:**
1. Ir a Meteorología → Reportes METAR
2. Crear nuevo registro
3. Introducir código OACI de 4 letras (ej: LECU)
4. Clic en "Obtener METAR"
5. Ver datos en pestañas "METAR Completo" y "Datos Decodificados"

**⚠️ Importante - Datos Históricos:**

Los METAR almacenados son **reportes históricos** del momento de la consulta:
- La vista lista muestra el estado cuando se obtuvo el METAR
- Para datos actuales, abrir el registro y clic en "Obtener METAR" nuevamente
- El campo `observation_time` indica cuándo se realizó la observación meteorológica
- El campo `fecha_consulta` indica cuándo se consultó desde Odoo
- Usa el chatter para ver el historial de actualizaciones

**Actualizar METAR existente:**
```python
# Método 1: Desde la interfaz
# - Abrir registro METAR
# - Clic en "Obtener METAR"
# - Los datos se actualizan automáticamente

# Método 2: Programáticamente
metar = self.env['leulit.meteo.metar'].browse(metar_id)
metar.action_obtener_metar()
```

### Filtros y Búsquedas

**Filtros predefinidos:**
- **Clima Actual**: Muestra solo consultas de clima actual
- **Pronóstico**: Muestra solo consultas de pronóstico
- **Hoy**: Consultas realizadas hoy
- **Esta Semana**: Consultas de la semana actual
- **Mis Consultas**: Solo tus consultas

**Búsqueda por campos:**
```
Buscar por:
- Código (METEO-00001)
- Ubicación (Madrid, LECU)
- Usuario
- Fecha
```

**Agrupaciones:**
```
Agrupar por:
- Ubicación
- Tipo de consulta
- Usuario
- Fecha
```

---

## Integración Programática

### Método 1: API Helper del Módulo

```python
# Uso recomendado desde otros módulos
meteo_obj = self.env['leulit.meteo.consulta']

datos = meteo_obj.consultar_clima_ubicacion(
    ubicacion='Madrid LECU',
    latitud=40.3717,
    longitud=-3.7856
)

if datos:
    # Acceder a datos
    consulta_id = datos['consulta_id']
    temperatura = datos['temperatura']
    viento = datos['viento']
    humedad = datos['humedad']
    descripcion = datos['descripcion']
    
    # Usar en tu lógica
    self.write({
        'temperatura_registro': temperatura,
        'meteo_consulta_id': consulta_id
    })
```

### Método 2: Crear Consulta y Llamar Manualmente

```python
# Crear registro de consulta
consulta = self.env['leulit.meteo.consulta'].create({
    'ubicacion': 'Barcelona El Prat',
    'latitud': 41.2974,
    'longitud': 2.0833,
    'notas': 'Consulta automática desde vuelo',
})

# Ejecutar consulta
consulta.action_consultar_clima_actual()

# Acceder a datos
temperatura = consulta.temperatura
descripcion = consulta.descripcion_clima
viento = consulta.velocidad_viento
```

### Método 3: Acceso Directo a la API

```python
from odoo.addons.leulit_meteo.models.leulit_meteo_service import OpenMeteoService

# Consultar directamente (sin crear registro en BD)
data = OpenMeteoService.get_current_weather(
    latitude=40.3717,
    longitude=-3.7856
)

if data and 'current' in data:
    current = data['current']
    temperatura = current.get('temperature_2m')
    viento = current.get('wind_speed_10m')
    humedad = current.get('relative_humidity_2m')
    
    # Traducir código de clima
    codigo = current.get('weather_code')
    descripcion = OpenMeteoService.get_weather_description(codigo)
```

### Método 4: Obtener Pronóstico

```python
# Pronóstico de 7 días
data = OpenMeteoService.get_forecast(
    latitude=40.3717,
    longitude=-3.7856,
    days=7
)

if data and 'daily' in data:
    daily = data['daily']
    fechas = daily['time']  # Lista de fechas
    temp_max = daily['temperature_2m_max']  # Temperaturas máximas
    temp_min = daily['temperature_2m_min']  # Temperaturas mínimas
    precipitacion = daily['precipitation_sum']  # Precipitación
    
    # Procesar pronóstico
    for i, fecha in enumerate(fechas):
        _logger.info(
            f"Fecha: {fecha}, Temp: {temp_min[i]}-{temp_max[i]}°C, "
            f"Precip: {precipitacion[i]}mm"
        )
```

---

## Casos de Uso Comunes

### Caso 1: Vincular Meteorología a Vuelo

**Objetivo:** Registrar condiciones meteorológicas al crear un vuelo

```python
# En leulit_operaciones, heredar modelo de vuelo
class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'
    
    # Añadir campo
    meteo_consulta_id = fields.Many2one(
        'leulit.meteo.consulta',
        string='Condiciones Meteorológicas'
    )
    
    # Método para obtener meteo al confirmar vuelo
    def action_confirmar_vuelo(self):
        res = super().action_confirmar_vuelo()
        
        # Obtener meteo del aeródromo de salida
        if self.aerodromo_salida_id:
            meteo_obj = self.env['leulit.meteo.consulta']
            datos = meteo_obj.consultar_clima_ubicacion(
                ubicacion=f"{self.aerodromo_salida_id.name}",
                latitud=self.aerodromo_salida_id.latitud,
                longitud=self.aerodromo_salida_id.longitud
            )
            
            if datos:
                self.meteo_consulta_id = datos['consulta_id']
                self.message_post(
                    body=f"Condiciones meteorológicas: {datos['descripcion']}, "
                         f"Temp: {datos['temperatura']}°C, "
                         f"Viento: {datos['viento']} km/h"
                )
        
        return res
```

### Caso 2: Verificar Condiciones Antes de Vuelo

**Objetivo:** Validar que las condiciones sean aptas para volar

```python
def check_condiciones_meteo(self):
    """Valida condiciones meteorológicas antes de vuelo"""
    
    # Consultar clima
    meteo_obj = self.env['leulit.meteo.consulta']
    datos = meteo_obj.consultar_clima_ubicacion(
        ubicacion=self.aerodromo_salida_id.name,
        latitud=self.aerodromo_salida_id.latitud,
        longitud=self.aerodromo_salida_id.longitud
    )
    
    if not datos:
        raise UserError(_('No se pudo obtener información meteorológica.'))
    
    # Verificar condiciones
    alertas = []
    
    # Viento máximo 40 km/h para helicóptero ligero
    if datos['viento'] > 40:
        alertas.append(f"⚠️ Viento fuerte: {datos['viento']} km/h")
    
    # Visibilidad: rechazar si hay tormenta o nieve intensa
    consulta = self.env['leulit.meteo.consulta'].browse(datos['consulta_id'])
    if consulta.codigo_clima in [95, 96, 99, 75, 86]:
        alertas.append(f"⚠️ Condiciones adversas: {consulta.descripcion_clima}")
    
    # Temperatura extrema
    if datos['temperatura'] < -10 or datos['temperatura'] > 45:
        alertas.append(f"⚠️ Temperatura extrema: {datos['temperatura']}°C")
    
    # Mostrar alertas si existen
    if alertas:
        mensaje = '\n'.join(alertas)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Advertencias Meteorológicas'),
                'message': mensaje,
                'type': 'warning',
                'sticky': True,
            }
        }
    
    return True
```

### Caso 3: Dashboard Meteorológico

**Objetivo:** Mostrar clima de múltiples bases

```python
def get_dashboard_meteo(self):
    """Obtiene datos meteorológicos de todas las bases"""
    
    bases = [
        {'nombre': 'Madrid LECU', 'lat': 40.3717, 'lon': -3.7856},
        {'nombre': 'Barcelona LEBL', 'lat': 41.2974, 'lon': 2.0833},
        {'nombre': 'Sevilla LEZL', 'lat': 37.4180, 'lon': -5.8931},
    ]
    
    meteo_obj = self.env['leulit.meteo.consulta']
    resultados = []
    
    for base in bases:
        datos = meteo_obj.consultar_clima_ubicacion(
            ubicacion=base['nombre'],
            latitud=base['lat'],
            longitud=base['lon']
        )
        
        if datos:
            resultados.append({
                'base': base['nombre'],
                'temperatura': datos['temperatura'],
                'descripcion': datos['descripcion'],
                'viento': datos['viento'],
                'humedad': datos['humedad'],
            })
    
    return resultados
```

### Caso 4: Reporte de Vuelo con Datos Meteorológicos

**Objetivo:** Incluir datos meteorológicos en informes

```xml
<!-- En el template del reporte -->
<div class="row mt-3" t-if="doc.meteo_consulta_id">
    <div class="col-12">
        <h5>Condiciones Meteorológicas</h5>
        <table class="table table-sm">
            <tr>
                <td><strong>Ubicación:</strong></td>
                <td><t t-esc="doc.meteo_consulta_id.ubicacion"/></td>
                <td><strong>Fecha Consulta:</strong></td>
                <td><t t-esc="doc.meteo_consulta_id.fecha_consulta"/></td>
            </tr>
            <tr>
                <td><strong>Condiciones:</strong></td>
                <td><t t-esc="doc.meteo_consulta_id.descripcion_clima"/></td>
                <td><strong>Temperatura:</strong></td>
                <td><t t-esc="doc.meteo_consulta_id.temperatura"/> °C</td>
            </tr>
            <tr>
                <td><strong>Viento:</strong></td>
                <td><t t-esc="doc.meteo_consulta_id.velocidad_viento"/> km/h</td>
                <td><strong>Humedad:</strong></td>
                <td><t t-esc="doc.meteo_consulta_id.humedad"/> %</td>
            </tr>
        </table>
    </div>
</div>
```

---

## Mejores Prácticas

### 1. Caché de Consultas

Evita consultar la API repetidamente para la misma ubicación y tiempo:

```python
def get_meteo_cached(self, ubicacion, latitud, longitud, max_age_hours=1):
    """Obtiene meteo desde caché o API si es necesario"""
    
    # Buscar consulta reciente
    limite_tiempo = fields.Datetime.now() - timedelta(hours=max_age_hours)
    consulta = self.env['leulit.meteo.consulta'].search([
        ('ubicacion', '=', ubicacion),
        ('latitud', '=', latitud),
        ('longitud', '=', longitud),
        ('tipo_consulta', '=', 'actual'),
        ('fecha_consulta', '>=', limite_tiempo),
    ], limit=1, order='fecha_consulta desc')
    
    if consulta:
        # Usar datos en caché
        return {
            'consulta_id': consulta.id,
            'temperatura': consulta.temperatura,
            'viento': consulta.velocidad_viento,
            'descripcion': consulta.descripcion_clima,
            'humedad': consulta.humedad,
            'desde_cache': True,
        }
    else:
        # Consultar API
        return self.consultar_clima_ubicacion(ubicacion, latitud, longitud)
```

### 2. Manejo de Errores

Siempre valida los datos recibidos:

```python
try:
    datos = meteo_obj.consultar_clima_ubicacion(...)
    if datos:
        self.temperatura = datos['temperatura']
    else:
        _logger.warning('No se pudieron obtener datos meteorológicos')
        # Continuar sin datos meteo
except Exception as e:
    _logger.error(f'Error al consultar meteorología: {str(e)}')
    # No bloquear el proceso principal
```

### 3. Consultas Asíncronas

Para no bloquear la UI en consultas múltiples:

```python
@api.model
def actualizar_meteo_bases_async(self):
    """Actualiza meteorología de todas las bases en background"""
    
    bases = self.env['res.partner'].search([
        ('es_aerodromo', '=', True),
        ('latitud', '!=', False),
        ('longitud', '!=', False),
    ])
    
    for base in bases:
        try:
            self.env['leulit.meteo.consulta'].with_delay().consultar_clima_ubicacion(
                ubicacion=base.name,
                latitud=base.latitud,
                longitud=base.longitud
            )
        except Exception as e:
            _logger.error(f'Error actualizando meteo para {base.name}: {e}')
            continue
```

### 4. Coordinadas Precisas

Asegúrate de que las coordenadas sean correctas:

```python
# Validación de coordenadas
@api.constrains('latitud', 'longitud')
def _check_coordenadas(self):
    for record in self:
        if not (-90 <= record.latitud <= 90):
            raise ValidationError(_('La latitud debe estar entre -90 y 90 grados.'))
        if not (-180 <= record.longitud <= 180):
            raise ValidationError(_('La longitud debe estar entre -180 y 180 grados.'))
```

### 5. Logging Apropiado

```python
import logging
_logger = logging.getLogger(__name__)

# Nivel INFO para eventos normales
_logger.info(f'Consultando meteo para {ubicacion}')

# Nivel WARNING para situaciones inusuales pero no críticas
_logger.warning(f'Datos meteo no disponibles para {ubicacion}')

# Nivel ERROR para errores que requieren atención
_logger.error(f'Error en API Open-Meteo: {str(e)}', exc_info=True)
```

---

## Ejemplos Avanzados

### Widget Personalizado para Mostrar Clima

```javascript
// En static/src/js/weather_widget.js
odoo.define('leulit_meteo.WeatherWidget', function (require) {
    'use strict';
    
    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');
    
    var WeatherWidget = AbstractField.extend({
        template: 'WeatherWidget',
        
        _renderReadonly: function () {
            this.$el.html(this._getWeatherHTML());
        },
        
        _getWeatherHTML: function () {
            var consulta = this.recordData;
            return `
                <div class="weather-display">
                    <span class="weather-icon">${this._getWeatherIcon(consulta.codigo_clima)}</span>
                    <span class="weather-temp">${consulta.temperatura}°C</span>
                    <span class="weather-desc">${consulta.descripcion_clima}</span>
                </div>
            `;
        },
        
        _getWeatherIcon: function(code) {
            // Retornar emoji según código
            if (code === 0) return '☀️';
            if (code <= 3) return '⛅';
            if (code <= 48) return '🌫️';
            if (code <= 67) return '🌧️';
            if (code <= 77) return '❄️';
            if (code <= 82) return '🌦️';
            if (code >= 95) return '⛈️';
            return '🌤️';
        },
    });
    
    fieldRegistry.add('weather_display', WeatherWidget);
    
    return WeatherWidget;
});
```

---

**Fin de la Guía de Uso**

Para más información, consulta:
- README.md - Información general
- __doc__.py - Documentación técnica completa
- index.html - Documentación web del módulo
