# Instalación del Módulo leulit_meteo - Nueva Versión

Este módulo ha sido actualizado con nuevas funcionalidades:
- ✅ Integración con Windy API (datos REST + visualización iframe)
- ✅ Widget de mapa interactivo con Leaflet para selección de ubicaciones
- ✅ Soporte para polilíneas/rutas con múltiples waypoints
- ✅ Sistema de plantillas de rutas predefinidas
- ✅ Resumen automático de condiciones meteorológicas de rutas
- ✅ Visualización dual: datos numéricos + mapa visual Windy

## Pasos de Instalación/Actualización

### 1. Verificar Dependencias

El módulo ya no requiere dependencias Python adicionales más allá de `requests` que ya estaba instalado.

### 2. Actualizar el Módulo en Odoo

```bash
# Opción 1: Desde la interfaz de Odoo
# - Ir a Aplicaciones
# - Buscar "leulit_meteo"
# - Click en "Actualizar"

# Opción 2: Desde terminal Docker
docker exec -ti helipistas_odoo odoo -u leulit_meteo -d nombre_bd --stop-after-init
```

### 3. Configurar Windy API (Opcional pero Recomendado)

1. Obtener API Key gratuita en: https://api.windy.com/keys
2. En Odoo: **Ajustes > Meteorología**
3. Ingresar API Key y seleccionar modelo (GFS recomendado)
4. Click en "Validar API Key"

## Nuevos Modelos y Campos

El módulo agrega:

### Modelos
- `leulit.meteo.consulta.punto`: Para puntos de polilíneas
- `leulit.meteo.ruta.template`: Plantillas de rutas reutilizables
- `leulit.meteo.ruta.template.punto`: Puntos de las plantillas

### Campos en `leulit.meteo.consulta`
- `fuente_datos`: Selection (openmeteo/windy)
- `es_polilinea`: Boolean
- `ruta_template_id`: Many2one a plantilla de ruta
- `puntos_ids`: One2many a puntos
- `numero_puntos`: Integer computed
- `puntos_geojson`: Text para widget de mapa
- `temperatura_min/max`: Float computed (resumen ruta)
- `viento_max`: Float computed
- `condiciones_criticas`: Boolean computed

### Nuevas Vistas
- Widget de mapa interactivo con Leaflet (selección ubicaciones)
- Iframe de Windy embed (visualización meteorológica)
- Pestaña "Puntos de Ruta" para polilíneas
- Pestaña "Mapa Windy Visual" con iframe embebido
- Configuración de Windy en Ajustes
- Gestión de Rutas Predefinidas (tree, form)
Simple con Mapa Interactivo

1. Crear nueva consulta meteorológica
2. Seleccionar "Fuente de Datos: Windy"
3. En "Mapa Interactivo", click en ubicación deseada
4. Click "Consultar Windy"
5. Ver datos en pestaña "Datos Actuales"
6. Ver visualización en pestaña "Mapa Windy Visual"

### Crear Ruta de Vuelo (Polilínea)

**Opción A: Crear desde cero**
1. Nueva consulta, marcar "¿Es Polilínea?"
2. Click en el mapa para agregar waypoints secuencialmente
3. Click derecho en un punto para eliminarlo
4. Arrastra markers para ajustar posición
5. Click "Guardar Ruta"
6. Seleccionar "Fuente: Windy" y click "Consultar Windy"
7. Ver datos por punto en pestaña "Puntos de Ruta"
8. Ver mapa visual en pestaña "Mapa Windy Visual"

**Opción B: Usar ruta predefinida**
1. Ir a Meteorología → Rutas Predefinidas
2. Crear ruta: "LEMD-LEBL" con waypoints
3. En nueva consulta, campo "Cargar Ruta Predefinida" → seleccionar "LEMD-LEBL"
4. Click "Cargar Ruta" → puntos se importan automáticamente
5. Click "Consultar Windy"

### Visualizar Condiciones Meteorológicas

**Datos Numéricos** (Pestaña "Puntos de Ruta"):
- Tabla con temperatura, viento, presión por waypoint
- Editable: agregar/eliminar puntos
- Exportable a Excel

**Mapa Visual** (Pestaña "Mapa Windy Visual"):
- Iframe con overlay animado de Windy
- Capas: viento, temperatura, nubes, precipitación
- Timeline para ver evolución temporal
- Zoom y navegación interactiva

**Resumen** (Campos superiores):
- Temperatura Min/Max en toda la ruta
- Viento Máximo encontrado
- ⚠️ Alerta si condiciones críticas (viento > 50 km/h o temp < 0°C)
### Crear Ruta de Vuelo

1. Nueva consulta, marcar "¿Es Polilínea?"
2. Click en el mapa para agregar waypoints
3. Click derecho en un punto para eliminarlo
4. Arrastra markers para ajustar
5. Click "Guardar Ruta"
6. Seleccionar "Fuente: Windy" y click "Consultar Windy"
7. Ver datos meteorológicos por punto en pestaña "Puntos de Ruta"

## Solución de Problemas

### El mapa no se muestra
- Verificar que el navegador permite contenido desde unpkg.com (CDN)
- Verificar en consola del navegador si hay errores de carga de Leaflet
- Limpiar caché del navegador

### Error "Leaflet no está cargado"
- Refrescar la página con Ctrl+F5 (forzar recarga de assets)
- Verificar conexión a internet (requiere CDN)

### API Key de Windy no válida
- Verificar que copiaste la key completa sin espacios
- La key puede tardar unos minutos en activarse tras registro
- Verificar límites de uso (plan gratuito ~1000 consultas/mes)

### Los puntos de polilínea no se guardan
- Asegurarse de hacer click en "Guardar Ruta" antes de salir
- Verificar permisos del usuario (requiere RBase_employee para crear)

## Documentación Completa

Ver archivos:
- `README.md`: Visión general y características
- `USAGE.md`: Guía detallada de uso con ejemplos

## Soporte

Para dudas o problemas:
1. Revisar logs de Odoo: `docker logs -f helipistas_odoo`
2. Verificar errores en consola del navegador (F12)
3. Consultar documentación de las APIs:
   - Open-Meteo: https://open-meteo.com/en/docs
   - Windy: https://api.windy.com/
   - Leaflet: https://leafletjs.com/
