# Flujo de Trabajo - leulit_meteo

## Arquitectura de la Solución

El módulo `leulit_meteo` tiene **3 capas de funcionalidad**:

### 1. **Selección de Ubicaciones** (Mapa Leaflet)
- Widget OWL interactivo con OpenStreetMap
- Permite seleccionar puntos individuales o polilíneas
- Los usuarios hacen clic en el mapa para definir ubicaciones

### 2. **Obtención de Datos** (APIs REST)
- **Open-Meteo API**: Datos meteorológicos generales
- **Windy API**: Modelos profesionales (GFS, ECMWF)
- **Aviation Weather API**: METAR aeronáuticos
- Los datos se obtienen vía llamadas REST y se almacenan en BD

### 3. **Visualización** (Tres formas)
- **Tabla de Puntos**: Datos numéricos en tabla editable
- **Resumen de Ruta**: Indicadores clave (temp min/max, viento max)
- **Mapa Visual Windy**: Iframe con overlay meteorológico animado

---

## Flujo Completo de Uso

```
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: Definir Ubicación/Ruta                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Opción A: Punto Único                                      │
│  ├── Click en mapa Leaflet → establece lat/lon             │
│  └── O introducir coordenadas manualmente                   │
│                                                              │
│  Opción B: Ruta (Polilínea)                                │
│  ├── Marcar "¿Es Polilínea?"                               │
│  ├── Click múltiples veces en mapa → crea waypoints       │
│  └── Click "Guardar Ruta"                                  │
│                                                              │
│  Opción C: Cargar Ruta Predefinida                         │
│  ├── Seleccionar de dropdown "Cargar Ruta Predefinida"    │
│  ├── Elige una ruta guardada (ej: LEMD-LEBL)              │
│  └── Click "Cargar Ruta" → puntos se cargan auto          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: Seleccionar Fuente de Datos                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Radio Button "Fuente de Datos":                            │
│  ○ Open-Meteo (gratuito, sin API key)                      │
│  ○ Windy (profesional, requiere API key)                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: Consultar API                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Si Open-Meteo:                                             │
│  └── Click "Consultar Clima Actual" o "Obtener Pronóstico"│
│                                                              │
│  Si Windy:                                                  │
│  └── Click "Consultar Windy"                               │
│      ├── Si punto único: consulta 1 punto                  │
│      └── Si polilínea: consulta N puntos (batch)           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 4: Ver Resultados                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PESTAÑA 1: "Mapa Windy Visual" (solo si Windy)            │
│  ├── Iframe embebido de embed.windy.com                    │
│  ├── Overlay meteorológico animado (viento, nubes, etc.)   │
│  ├── Controles interactivos de Windy                       │
│  └── Cambia capas: viento → temperatura → nubes → lluvia   │
│                                                              │
│  PESTAÑA 2: "Datos Actuales" (punto único)                 │
│  └── Campos con datos numéricos (temp, viento, humedad)    │
│                                                              │
│  PESTAÑA 3: "Puntos de Ruta" (polilíneas)                  │
│  ├── Tabla con todos los waypoints                         │
│  ├── Cada fila: punto + datos meteo de ese punto           │
│  └── Editable: puedes agregar/eliminar puntos              │
│                                                              │
│  RESUMEN (para rutas):                                      │
│  ├── Temp Min/Max en toda la ruta                          │
│  ├── Viento Max en toda la ruta                            │
│  └── Advertencia si condiciones críticas                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 5: (Opcional) Guardar Ruta como Plantilla            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Si quieres reutilizar esta ruta:                           │
│  └── Click "Guardar como Plantilla"                        │
│      ├── Se crea entrada en "Rutas Predefinidas"           │
│      └── Disponible en dropdown para futuras consultas     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Clave

### A. Widget de Mapa (Leaflet)

**Ubicación**: `static/src/js/meteo_map_widget.js`

**Función**: Selección visual de ubicaciones

**Características**:
- Modo Punto: Un marker arrastrable
- Modo Polilínea: Múltiples markers + línea conectora
- Click para agregar, click derecho para eliminar
- Botones: limpiar, centrar, guardar

**NO ES** el mapa visual meteorológico de Windy (ese es el iframe)

### B. Iframe de Windy

**Ubicación**: Pestaña "Mapa Windy Visual" en formulario de consulta

**URL generada**: `get_windy_embed_url()` en modelo

**Ejemplo**:
```
https://embed.windy.com/embed2.html?
  lat=40.416&lon=-3.703&zoom=9&
  level=surface&overlay=wind&product=ecmwf&
  metricWind=km/h&metricTemp=°C
```

**Función**: Visualización rica de condiciones meteorológicas
- Overlay animado de viento
- Capas seleccionables (temperatura, nubes, lluvia, presión)
- Timeline para ver evolución temporal
- NO requiere API Key de Windy (la visualización es pública)

### C. Selector de Rutas

**Modelo**: `leulit.meteo.ruta.template`

**Función**: Biblioteca de rutas preconfiguradas

**Casos de uso**:
- Rutas de vuelo frecuentes (LEMD→LEBL)
- Patrullas habituales
- Zonas de operación recurrentes

**Workflow**:
1. Crear ruta en "Rutas Predefinidas"
2. Definir waypoints con nombres (LEMD, GOPSA, LEBL)
3. En consulta nueva, seleccionar del dropdown
4. Click "Cargar Ruta" → puntos se importan

---

## Diferencia Clave: Mapa Leaflet vs Iframe Windy

| Característica | Mapa Leaflet | Iframe Windy |
|----------------|--------------|--------------|
| **Propósito** | Seleccionar ubicaciones | Visualizar condiciones meteo |
| **Interacción** | Click para marcar puntos | Solo visualización (zoom, pan) |
| **Overlay Meteo** | ❌ No | ✅ Sí (animado) |
| **Edición** | ✅ Agregar/mover/eliminar puntos | ❌ Solo ver |
| **Requiere API Key** | ❌ No | ❌ No (embed público) |
| **Ubicación** | Sección "Mapa Interactivo" | Pestaña "Mapa Windy Visual" |

---

## Ejemplo Práctico: Consulta de Ruta

### Escenario: Vuelo Barcelona → Valencia

**1. Crear Consulta**
- Meteorología → Consultas → Crear
- Nombre: "Ruta LEBL-LEVC"
- Marcar "¿Es Polilínea?"
- Fuente: Windy

**2. Definir Waypoints (en Mapa Leaflet)**
- Click en Barcelona (41.297, 2.078)
- Click en Tarragona (41.119, 1.245)
- Click en Castellón (39.987, -0.023)
- Click en Valencia (39.489, -0.482)
- Click "Guardar Ruta"

**3. Consultar Windy API**
- Click botón "Consultar Windy"
- Sistema consulta 4 puntos automáticamente
- Datos se guardan en tabla "Puntos de Ruta"

**4. Visualizar Resultados**

**Pestaña "Mapa Windy Visual"**:
- Iframe muestra mapa de España
- Overlay de viento animado visible
- Puedes cambiar a capa de temperatura, nubes, etc.
- Timeline muestra evolución próximas horas

**Pestaña "Puntos de Ruta"**:
```
| Punto | Nombre      | Temp | Viento | Nubes |
|-------|-------------|------|--------|-------|
| 1     | Barcelona   | 18°C | 15km/h | 30%   |
| 2     | Tarragona   | 17°C | 20km/h | 45%   |
| 3     | Castellón   | 19°C | 18km/h | 35%   |
| 4     | Valencia    | 20°C | 12km/h | 20%   |
```

**Resumen**:
- Temp Min: 17°C
- Temp Max: 20°C
- Viento Max: 20 km/h
- Condiciones Críticas: ❌ No

**5. Guardar como Plantilla**
- Click "Guardar como Plantilla"
- Ahora aparece en "Rutas Predefinidas"
- Próxima vez: seleccionar del dropdown y cargar

---

## APIs Usadas y sus Roles

### Open-Meteo
- **URL**: https://api.open-meteo.com/v1/forecast
- **Uso**: Clima general gratuito
- **Datos**: Temp, humedad, precipitación, viento básico
- **Sin API Key**

### Windy API (REST)
- **URL**: https://api.windy.com/api/point-forecast/v2
- **Uso**: Datos numéricos profesionales
- **Datos**: Modelos GFS/ECMWF, viento preciso, presión, punto rocío
- **Requiere API Key** (configurar en Ajustes)

### Windy Embed (Iframe)
- **URL**: https://embed.windy.com/embed2.html
- **Uso**: Visualización gráfica animada
- **Datos**: Overlay visual de condiciones
- **Sin API Key** (embed público)

### Aviation Weather
- **URL**: https://aviationweather.gov/cgi-bin/data/dataserver.php
- **Uso**: METAR oficiales
- **Datos**: Reportes aeronáuticos
- **Sin API Key**

---

## Preguntas Frecuentes

**¿Por qué hay DOS mapas?**
- **Leaflet**: Para que TÚ selecciones ubicaciones (input)
- **Windy iframe**: Para VER condiciones meteorológicas (output)

**¿Cuándo usar Open-Meteo vs Windy?**
- **Open-Meteo**: Consultas simples, sin API key
- **Windy**: Rutas complejas, vientos precisos, modelos profesionales

**¿El iframe de Windy requiere API Key?**
- NO. El embed de Windy es público.
- La API Key solo se necesita para llamadas REST (datos numéricos)

**¿Puedo ver el Windy iframe sin consultar la API?**
- SÍ. El iframe se muestra siempre que selecciones "Fuente: Windy"
- Muestra condiciones generales de la zona
- Con la API obtienes números exactos por punto

**¿Cómo uso las Rutas Predefinidas?**
1. Menú: Meteorología → Rutas Predefinidas
2. Crear nueva ruta, definir waypoints
3. Al crear consulta, selector dropdown carga la ruta
4. Click "Cargar Ruta", puntos se importan automáticamente

---

## Próximos Pasos

Para usar el módulo completo:

1. **Actualizar módulo** en Odoo
2. **Configurar Windy API Key** (opcional): Ajustes → Meteorología
3. **Crear rutas habituales**: Meteorología → Rutas Predefinidas
4. **Usar en planificación**: Antes de volar, consultar condiciones de la ruta
