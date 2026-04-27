# Leulit Meteorología

Módulo Odoo para consulta meteorológica orientada a operaciones aeronáuticas: clima actual y pronóstico por punto o ruta, mapa interactivo Leaflet, plantillas de rutas reutilizables, visor Windy embebido y briefings METAR/TAF/SIGMET oficiales de AEMET OpenData (texto RAW intacto). Sistema de aeródromos de referencia para puntos sin METAR propio.

## Características

- Clima actual y pronóstico por punto vía Open-Meteo (sin API key).
- Modelos profesionales de Windy (GFS, ECMWF, ICON, ICON-EU, NAM) para punto único o polilínea, con API key.
- Mapa interactivo Leaflet/OpenStreetMap para seleccionar visualmente puntos o trazar rutas con waypoints.
- Plantillas de rutas reutilizables (p.ej. LEMD-LEBL) cargables en cualquier consulta.
- Resumen automático de la ruta: temperatura mín./máx., viento máximo y alerta de condiciones críticas.
- Iframe Windy embebido para visualización animada de capas (no requiere key).
- Briefings **METAR + TAF + SIGMET oficiales** de AEMET OpenData (texto RAW intacto, válido a efectos legales/AESA). Sistema de aeródromos de referencia (`leulit.meteo.icao.reference`) para resolver FIR y redirigir helipuertos sin METAR propio al aeródromo cercano. Arquitectura de proveedores pluggable: añadir nuevas fuentes (NOAA, etc.) no requiere tocar el modelo ni las vistas.
- Histórico de consultas vinculable a otros módulos (vuelos, operaciones, etc.) mediante Many2one.

## APIs externas

información swagger--> https://opendata.aemet.es/dist/index.html?

| API | URL base | Requiere key | Uso en el módulo |
|-----|----------|--------------|------------------|
| Open-Meteo | `https://api.open-meteo.com/v1/forecast` | No | Clima actual y pronóstico (gratuita; aplican rate limits suaves para uso comercial). |
| Windy REST | `https://api.windy.com/api/point-forecast/v2` | Sí | Datos numéricos de modelos profesionales por punto o ruta. |
| Windy Embed | `https://embed.windy.com/embed2.html` | No | Iframe público con visualización animada. |
| AEMET OpenData | `https://opendata.aemet.es/opendata` | Sí (JWT) | Mensajes oficiales METAR/TAF/SIGMET por OACI (METAR/TAF) y por FIR (SIGMET). Patrón 2 llamadas: endpoint → URL `datos` con texto plano. RAW intacto (sin alterar). |

## Modelos principales

- `leulit.meteo.consulta` — consulta meteorológica para punto único o polilínea/ruta; soporta fuente Open-Meteo o Windy.
- `leulit.meteo.consulta.punto` — waypoints (One2many) de una consulta en modo ruta.
- `leulit.meteo.ruta.template` y `leulit.meteo.ruta.template.punto` — plantillas de rutas reutilizables.
- `leulit.meteo.metar` — briefing METAR/TAF/SIGMET independiente de proveedor; campo `provider` para seleccionar la fuente (hoy `aemet`).
- `leulit.meteo.icao.reference` — tabla de aeródromos OACI ↔ FIR + opcional `ref_icao` para puntos sin METAR propio.

Infraestructura de proveedores:

- `models/leulit_meteo_metar_provider.py` — interfaz abstracta `MetarProvider` + registro vía decorador `@register_provider` y helpers `get_provider(code)`, `provider_selection()`, `all_providers()`.
- `models/leulit_meteo_metar_aemet.py` — `AemetMetarProvider` (`code='aemet'`), única implementación actual; usa internamente `AemetOpenDataService`.

## Menú principal en Odoo

`Meteorología` →

- Consultas Clima
- Rutas Predefinidas
- Reportes METAR
- Aeródromos de Referencia (solo administradores)

La configuración (claves de Windy y AEMET, modelo Windy por defecto y botones de validación) está en `Meteorología → Configuración` (submenú dentro del módulo, accesible solo a administradores — `base.group_system`). Es un wizard (`TransientModel` `leulit.meteo.config`) que lee y escribe los siguientes parámetros del sistema:

- `leulit_meteo.windy_api_key`
- `leulit_meteo.windy_model` (gfs, ecmwf, icon, iconEu, nam)
- `leulit_meteo.aemet_api_key`

## Instalación abreviada

1. Instalar la dependencia Python `requests`.
2. Actualizar la lista de aplicaciones en Odoo e instalar **Leulit Meteorología**.
3. Configurar las API keys de Windy y AEMET en `Meteorología → Configuración`.

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
