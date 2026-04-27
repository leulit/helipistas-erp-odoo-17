# Leulit Meteorología

Módulo de integración con Open-Meteo y Aviation Weather para obtener información meteorológica en tiempo real.

## Características

- ☁️ **Consulta de Clima Actual**: Obtén temperatura, humedad, precipitación y viento (Open-Meteo)
- 📅 **Pronósticos**: Consulta pronósticos meteorológicos hasta 16 días (Open-Meteo)
- 🌪️ **Windy API**: Integración con modelos profesionales (GFS, ECMWF, ICON)
- 🗺️ **Mapa Interactivo**: Widget visual para seleccionar ubicaciones con Leaflet
- 🛣️ **Polilíneas/Rutas**: Define rutas de vuelo con múltiples waypoints
- ✈️ **Reportes METAR**: Obtén reportes meteorológicos aeronáuticos oficiales (Aviation Weather)
- 🛩️ **Categorías de Vuelo**: Clasificación automática VFR/MVFR/IFR/LIFR
- 📍 **Múltiples Ubicaciones**: Registra y consulta clima de diferentes ubicaciones
- 🔗 **Integración**: Vincula consultas con vuelos u otras operaciones
- 📊 **Histórico**: Mantén un registro de todas las consultas realizadas

## APIs Utilizadas

### 1. Open-Meteo (Clima General)
[Open-Meteo](https://open-meteo.com/) - API meteorológica gratuita y de código abierto.
- Datos meteorológicos globales
- Sin autenticación requerida
- Sin límites de uso

### 2. Windy (Modelos Profesionales)
[Windy API](https://api.windy.com/) - Modelos meteorológicos profesionales avanzados.
- Múltiples modelos: GFS, ECMWF, ICON, NAM
- Datos de viento de alta precisión
- Requiere API Key gratuita
- Límites según plan (gratuito: ~1000 consultas/mes)

### 3. Aviation Weather (METAR)
[Aviation Weather Center](https://aviationweather.gov/) - API oficial de datos meteorológicos aeronáuticos.
- Reportes METAR en tiempo real
- Datos TAF (Terminal Aerodrome Forecast)
- Categorías de vuelo (VFR/IFR)
- Sin autenticación requerida

### Datos Disponibles

**Open-Meteo (Clima General):**
- Temperatura actual y sensación térmica
- Humedad relativa
- Precipitación
- Cobertura de nubes
- Velocidad y dirección del viento
- Rachas de viento
- Códigos de condiciones meteorológicas WMO

**Aviation Weather (METAR):**
- Reporte METAR completo en texto

**Windy API:**
- Temperatura y punto de rocío
- Presión atmosférica (superficie)
- Humedad relativa
- Viento: velocidad, dirección y rachas (alta precisión)
- Cobertura de nubes por capas
- Precipitación acumulada
- Múltiples modelos (GFS, ECMWF, ICON, NAM)
- Datos por punto o polilínea (ruta)
- Temperatura y punto de rocío
- Viento (dirección, velocidad, rachas)
- Visibilidad
- QNH / Altímetro
- Categoría de vuelo (VFR/MVFR/IFR/LIFR)
- Información de nubes
- Fenómenos meteorológicos (lluvia, niebla, etc.)

## Instalación

### Dependencias Python

```bash
pip install requests
```

O en Docker:

```bash
docker exec -ti helipistas_odoo pip install requests
```

### Instalación del Módulo

1. Actualizar lista de aplicaciones
2. Buscar "Leulit Meteorología"
3. Hacer clic en "Instalar"

## Uso

### Crear una Consulta

1. Ir a **Meteorología > Consultas**
2. Hacer clic en **Crear**
3. Introducir:
   - Ubicación (ej: "Madrid - LECU")
   - Latitud (ej: 40.3717)
   - Longitud (ej: -3.7856)
4. Hacer clic en **Consultar Clima Actual** o **Obtener Pronóstico**

### Usar Mapa Interactivo

El módulo incluye un widget de mapa interactivo con Leaflet:

**Modo Punto Único:**
1. Crear nueva consulta
2. En la sección "Mapa Interactivo", hacer clic en el mapa
3. El marker se posiciona y las coordenadas se actualizan automáticamente
4. Arrastra el marker para ajustar la ubicación
5. Seleccionar fuente de datos (Open-Meteo o Windy)
6. Hacer clic en el botón de consulta correspondiente

**Modo Polilínea/Ruta:**
1. Marcar checkbox "¿Es Polilínea?"
2. Click en el mapa para agregar puntos secuencialmente
3. Se dibuja una línea conectando los puntos
4. Arrastra markers para reposicionar
5. Click derecho en un marker para eliminarlo
6. Hacer clic en "Guardar Ruta" para persistir los puntos
7. En la pestaña "Puntos de Ruta" edita nombres y altitudes
8. Hacer clic en "Consultar Windy" para obtener datos de todos los puntos

**Controles del Mapa:**
- **Modo: Ruta / Modo: Punto**: Alterna entre modos
- **Limpiar**: Elimina todos los markers
- **Centrar**: Ajusta vista a los markers actuales
- **Guardar Ruta**: Persiste puntos en la base de datos (solo polilínea)

### Consultar con Windy API

**Requisitos:**
1. Ir a **Ajustes > Meteorología**
2. Configurar Windy API Key (obtener en https://api.windy.com/keys)
3. Seleccionar modelo por defecto (GFS, ECMWF, ICON, etc.)
4. Hacer clic en "Validar API Key"

**Consulta Simple:**
1. Crear consulta con ubicación
2. Seleccionar "Fuente de Datos: Windy"
3. Hacer clic en "Consultar Windy"
4. Ver datos actualizados (temperatura, viento de precisión, presión, etc.)

**Consulta de Ruta:**
1. Crear consulta en modo polilínea
2. Definir waypoints en el mapa
3. Guardar ruta
4. Seleccionar "Fuente de Datos: Windy"
5. Hacer clic en "Consultar Windy"
6. Ver datos meteorológicos de cada punto en "Puntos de Ruta"

### Visualización de Datos Windy

Los datos de Windy se muestran en **dos formas**:

**1. Mapa Visual Animado** (Pestaña "Mapa Windy Visual"):
- Iframe embebido de Windy con overlay meteorológico
- Visualización animada de viento, temperatura, nubes
- Cambia capas con controles interactivos
- Timeline para ver evolución temporal
- **NO requiere API Key** (embed público)

**2. Datos Numéricos** (Pestaña "Puntos de Ruta"):
- Tabla con temperatura, viento, presión por punto
- Resumen: temp min/max, viento máximo
- Alerta de condiciones críticas
- **Requiere API Key** (datos de la API REST)

### Obtener un METAR

1. Ir a **Meteorología > Reportes METAR**
2. Hacer clic en **Crear**
3. Introducir código OACI (4 letras): **LECU**
4. Hacer clic en **Obtener METAR**
5. Ver reporte completo y datos decodificados

**⚠️ Nota Importante - Datos Históricos**: Los METAR son reportes históricos. La vista muestra el estado del momento en que se consultó la API, no datos en tiempo real. Para actualizar:
- Abrir el registro existente
- Hacer clic en **Obtener METAR** nuevamente
- Los datos se actualizarán con el METAR más reciente
- El campo `observation_time` indica cuándo se realizó la observación
- El campo `fecha_consulta` indica cuándo se consultó desde Odoo

### Usar Rutas Predefinidas

El módulo incluye sistema de **plantillas de rutas** para reutilizar rutas comunes:

**Crear Plantilla**:
1. Ir a **Meteorología > Rutas Predefinidas**
2. Crear nueva: "LEMD-LEBL"
3. Definir waypoints con coordenadas
4. Guardar

**Usar en Consulta**:
1. Nueva consulta meteorológica
2. Campo "Cargar Ruta Predefinida" → seleccionar ruta
3. Click "Cargar Ruta" → puntos se importan automáticamente
4. Consultar Windy para obtener datos de toda la ruta

**Guardar Consulta como Plantilla**:
1. Después de crear ruta con el mapa
2. Click "Guardar como Plantilla"
3. Ahora disponible en selector para futuras consultas

### Categorías de Vuelo METAR

- **VFR** (Verde): Techo > 5000ft, Visibilidad > 5mi
- **MVFR** (Amarillo): Techo 3000-5000ft, Visibilidad 3-5mi
- **IFR** (Naranja): Techo 1000-3000ft, Visibilidad 1-3mi
- **LIFR** (Rojo): Techo < 1000ft, Visibilidad < 1mi

### Integración con Otros Módulos

Puedes llamar al servicio desde otros módulos:

### Consultar Clima (Open-Meteo)

```python
# Consultar clima desde cualquier módulo
meteo = self.env['leulit.meteo.consulta']
datos = meteo.consultar_clima_ubicacion(
    ubicacion='Madrid LECU',
    latitud=40.3717,
    longitud=-3.7856
)

if datos:
    temperatura = datos['temperatura']
    viento = datos['viento']
    descripcion = datos['descripcion']
```

### Obtener METAR Aeronáutico

```python
# Obtener METAR de un aeródromo
metar_obj = self.env['leulit.meteo.metar']
datos_metar = metar_obj.obtener_metar_aerodromo('LECU')

if datos_metar:
    metar_id = datos_metar['metar_id']
    raw = datos_metar['raw']
    temperatura = datos_metar['temperatura']
    viento = datos_metar['viento_velocidad']
    qnh = datos_metar['qnh']
    categoria = datos_metar['categoria_vuelo']  # VFR, MVFR, IFR, LIFR
```

### Ejemplo Integración con Vuelos

```python
# En leulit_operaciones
class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'
    
    metar_id = fields.Many2one('leulit.meteo.metar', string='METAR')
    
    def action_obtener_metar_salida(self):
        if self.aerodromo_salida_id.codigo_oaci:
            metar_obj = self.env['leulit.meteo.metar']
            datos = metar_obj.obtener_metar_aerodromo(
                self.aerodromo_salida_id.codigo_oaci
            )
            if datos:
                self.metar_id = datos['metar_id']
```

## Ejemplos de Ubicaciones

### Aeródromos Españoles

| Ubicación | Latitud | Longitud |
|-----------|---------|----------|
| Madrid - Cuatro Vientos (LECU) | 40.3717 | -3.7856 |
| Sabadell (LELL) | 41.5209 | 2.1050 |
| Granada - Armilla (LEGA) | 37.1331 | -3.6356 |
| Valencia (LEVC) | 39.4893 | -0.4816 |
| Sevilla (LEZL) | 37.4180 | -5.8931 |

## Notas Técnicas

- **Sin límites de rate**: Open-Meteo es gratuito y no requiere API key
- **Caché**: Considera implementar caché para evitar consultas repetidas
- **Timeout**: Las consultas tienen un timeout de 10 segundos
- **Errores**: Los errores se registran en el log de Odoo

## Soporte

Para más información sobre los datos disponibles, consulta la documentación oficial de Open-Meteo:
https://open-meteo.com/en/docs

## Autor

**Leulit**  
https://www.leulit.com

## Licencia

LGPL-3
