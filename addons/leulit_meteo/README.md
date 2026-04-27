# Leulit Meteorología

Módulo Odoo para consulta meteorológica orientada a operaciones aeronáuticas: clima actual y pronóstico por punto o ruta, mapa interactivo Leaflet, plantillas de rutas reutilizables, visor Windy embebido y reportes tipo METAR mediante una arquitectura de proveedores pluggable (actualmente AEMET para España, fácilmente extensible a otras fuentes).

## Características

- Clima actual y pronóstico por punto vía Open-Meteo (sin API key).
- Modelos profesionales de Windy (GFS, ECMWF, ICON, ICON-EU, NAM) para punto único o polilínea, con API key.
- Mapa interactivo Leaflet/OpenStreetMap para seleccionar visualmente puntos o trazar rutas con waypoints.
- Plantillas de rutas reutilizables (p.ej. LEMD-LEBL) cargables en cualquier consulta.
- Resumen automático de la ruta: temperatura mín./máx., viento máximo y alerta de condiciones críticas.
- Iframe Windy embebido para visualización animada de capas (no requiere key).
- Reportes tipo METAR mediante arquitectura de proveedores pluggable: actualmente AEMET (España) sintetizado desde observación horaria y etiquetado con `RMK AEMET`. Añadir nuevos proveedores no requiere tocar el modelo ni las vistas.
- Histórico de consultas vinculable a otros módulos (vuelos, operaciones, etc.) mediante Many2one.

## APIs externas

| API | URL base | Requiere key | Uso en el módulo |
|-----|----------|--------------|------------------|
| Open-Meteo | `https://api.open-meteo.com/v1/forecast` | No | Clima actual y pronóstico (gratuita; aplican rate limits suaves para uso comercial). |
| Windy REST | `https://api.windy.com/api/point-forecast/v2` | Sí | Datos numéricos de modelos profesionales por punto o ruta. |
| Windy Embed | `https://embed.windy.com/embed2.html` | No | Iframe público con visualización animada. |
| AEMET OpenData | `https://opendata.aemet.es/opendata` | Sí (JWT) | Observación horaria de estaciones españolas (patrón de 2 llamadas: endpoint → URL `datos`). AEMET **no** publica METAR oficiales; el módulo sintetiza un texto tipo METAR a partir de la observación. |

## Modelos principales

- `leulit.meteo.consulta` — consulta meteorológica para punto único o polilínea/ruta; soporta fuente Open-Meteo o Windy.
- `leulit.meteo.consulta.punto` — waypoints (One2many) de una consulta en modo ruta.
- `leulit.meteo.ruta.template` y `leulit.meteo.ruta.template.punto` — plantillas de rutas reutilizables.
- `leulit.meteo.metar` — reporte METAR independiente de proveedor; campo `provider` para seleccionar la fuente (hoy `aemet`).

Infraestructura de proveedores:

- `models/leulit_meteo_metar_provider.py` — interfaz abstracta `MetarProvider` + registro vía decorador `@register_provider` y helpers `get_provider(code)`, `provider_selection()`, `all_providers()`.
- `models/leulit_meteo_metar_aemet.py` — `AemetMetarProvider` (`code='aemet'`), única implementación actual; usa internamente `AemetOpenDataService`.

## Menú principal en Odoo

`Meteorología` →

- Consultas Clima
- Rutas Predefinidas
- Reportes METAR

La configuración (claves de Windy y AEMET, modelo Windy por defecto y botones de validación) está en `Ajustes → Meteorología`, sobre los parámetros del sistema:

- `leulit_meteo.windy_api_key`
- `leulit_meteo.windy_model` (gfs, ecmwf, icon, iconEu, nam)
- `leulit_meteo.aemet_api_key`

## Instalación abreviada

1. Instalar la dependencia Python `requests`.
2. Actualizar la lista de aplicaciones en Odoo e instalar **Leulit Meteorología**.
3. Configurar las API keys de Windy y AEMET en `Ajustes → Meteorología`.

Para el procedimiento detallado (Docker, permisos, validación de claves, troubleshooting) consulta [INSTALL.md](INSTALL.md).

## Documentación adicional

- [USAGE.md](USAGE.md) — Guía paso a paso de uso del módulo: creación de consultas, mapa interactivo, rutas, integración programática con otros módulos y ejemplos de código.
- [WORKFLOW.md](WORKFLOW.md) — Diagramas y flujo de datos entre vistas, modelos y APIs externas.

## Compatibilidad

Pensado para Odoo 16 (a pesar de que `__manifest__.py` declara `'version': '17.0.1.0.0'`).

Dependencias: `leulit`, `mail`. Dependencias externas Python: `requests`.

## Autor

**Leulit** — https://www.leulit.com

## Licencia

LGPL-3
