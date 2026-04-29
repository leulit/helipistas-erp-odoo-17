# Leulit Meteorología

Módulo Odoo para consulta meteorológica orientada a operaciones aeronáuticas: clima actual y pronóstico por punto o ruta, mapa interactivo Leaflet, plantillas de rutas reutilizables, visor Windy embebido y briefings METAR/TAF/SIGMET oficiales de AEMET OpenData (texto RAW intacto). Tabla de aeródromos de referencia (solo aeródromos con METAR/TAF real) con resolución en tiempo real de OACIs desconocidos y cron de actualización automática cada 10 minutos.

## Características

- Clima actual y pronóstico por punto vía Open-Meteo (sin API key).
- Modelos profesionales de Windy (GFS, ECMWF, ICON, ICON-EU, NAM) para punto único o polilínea, con API key.
- Mapa interactivo Leaflet/OpenStreetMap para seleccionar visualmente puntos o trazar rutas con waypoints.
- Plantillas de rutas reutilizables (p.ej. LEMD-LEBL) cargables en cualquier consulta.
- Resumen automático de la ruta: temperatura mín./máx., viento máximo y alerta de condiciones críticas.
- Iframe Windy embebido para visualización animada de capas (no requiere key).
- Briefings **METAR + TAF + SIGMET oficiales** de AEMET OpenData (texto RAW intacto, válido a efectos legales/AESA). Tabla de aeródromos de referencia (`leulit.meteo.icao.reference`) con solo aeródromos que emiten METAR/TAF real; resuelve FIR y localiza el aeródromo más cercano para OACIs sin servicio MET. Arquitectura de proveedores pluggable: añadir nuevas fuentes (NOAA, etc.) no requiere tocar el modelo ni las vistas.
- **Resolución en tiempo real de OACIs desconocidos**: cuando se pide un briefing para un OACI no registrado en la tabla, el sistema obtiene sus coordenadas vía OpenAIP (o CheckWX como fallback) y localiza por distancia haversine el aeródromo más cercano de la tabla de referencia. Devuelve su METAR/TAF sin crear ningún registro nuevo.
- **Histórico automático** (`leulit.meteo.historico`): cron cada 10 min que descarga y almacena METAR/TAF de todos los aeródromos activos.
- **Sincronización de la tabla de aeródromos** desde aviationweather.gov (NOAA/FAA): botón en Parámetros que actualiza la lista oficial de aeródromos españoles con METAR o TAF. No requiere API key.
- Histórico de consultas vinculable a otros módulos (vuelos, operaciones, etc.) mediante Many2one.

## APIs externas

Swagger AEMET → https://opendata.aemet.es/dist/index.html?

| API | URL base | Requiere key | Uso en el módulo |
|-----|----------|--------------|------------------|
| Open-Meteo | `https://api.open-meteo.com/v1/forecast` | No | Clima actual y pronóstico (gratuita). |
| Windy REST | `https://api.windy.com/api/point-forecast/v2` | Sí | Datos numéricos de modelos profesionales por punto o ruta. |
| Windy Embed | `https://embed.windy.com/embed2.html` | No | Iframe público con visualización animada. |
| AEMET OpenData | `https://opendata.aemet.es/opendata` | Sí (JWT) | Mensajes oficiales METAR/TAF/SIGMET por OACI (METAR/TAF) y por FIR (SIGMET). Patrón 2 llamadas: endpoint → URL `datos` con texto plano. RAW intacto (sin alterar). |
| OpenAIP | `https://api.openaip.net/api` | Sí | Coordenadas de un aeródromo por OACI. Fuente primaria para resolución de OACIs desconocidos. |
| CheckWX | `https://api.checkwx.com` | Sí | Coordenadas de aeródromo por OACI. Fallback cuando OpenAIP no devuelve resultado para un OACI desconocido. |
| Aviation Weather | `https://aviationweather.gov/api/data` / ADDS | No | METAR/TAF globales y listado de estaciones de NOAA/FAA. API pública gratuita (sin key). Fuente principal de sincronización de aeródromos. |

## Modelos principales

- `leulit.meteo.consulta` — consulta meteorológica para punto único o polilínea/ruta; soporta fuente Open-Meteo o Windy.
- `leulit.meteo.consulta.punto` — waypoints (One2many) de una consulta en modo ruta.
- `leulit.meteo.ruta.template` y `leulit.meteo.ruta.template.punto` — plantillas de rutas reutilizables.
- `leulit.meteo.metar` — briefing METAR/TAF/SIGMET independiente de proveedor; campo `provider` para seleccionar la fuente (hoy `aemet`).
- `leulit.meteo.icao.reference` — tabla de aeródromos OACI ↔ FIR. Contiene únicamente aeródromos con METAR/TAF real. Soporta cron de actualización automática. Campos destacados: `latitud`, `longitud`, `proxima_actualizacion`, `proveedor_oficial`.
- `leulit.meteo.historico` — histórico de METAR/TAF almacenado automáticamente por el cron para cada aeródromo de referencia. Vinculado a `icao_reference_id`.

Infraestructura de proveedores:

- `models/leulit_meteo_metar_provider.py` — interfaz abstracta `MetarProvider` + registro vía decorador `@register_provider` y helpers `get_provider(code)`, `provider_selection()`, `all_providers()`.
- `models/leulit_meteo_metar_aemet.py` — `AemetMetarProvider` (`code='aemet'`), única implementación actual; usa internamente `AemetOpenDataService`.

Servicios REST:

- `models/leulit_meteo_service.py` — `OpenMeteoService`.
- `models/leulit_meteo_windy_service.py` — `WindyService`.
- `models/leulit_meteo_aemet_service.py` — `AemetOpenDataService`.
- `models/leulit_meteo_checkwx_service.py` — `CheckWXService` (METAR/TAF/station internacional + búsqueda por radio).
- `models/leulit_meteo_openaip_service.py` — `OpenAIPService` (coordenadas y nombre de aeródromo por OACI).
- `models/leulit_meteo_aviation_weather_service.py` — `AviationWeatherService` (METAR/TAF de aviationweather.gov, API pública NOAA/FAA sin key).

## Menú principal en Odoo

`Meteorología` →

- Consultas Clima
- Rutas Predefinidas
- Reportes METAR
- Aeródromos de Referencia (solo administradores)

La configuración está en `Meteorología → Configuración`, con dos wizards de administrador (`base.group_system`):

### API Keys (`leulit.meteo.config`)

Gestiona las claves de los servicios externos. Cada servicio tiene su propia pestaña con descripción, campo de clave y botón "Probar conexión". Parámetros del sistema escritos:

- `leulit_meteo.windy_api_key`
- `leulit_meteo.windy_model` (gfs, ecmwf, icon, iconEu, nam)
- `leulit_meteo.aemet_api_key`
- `leulit_meteo.openaip_api_key`
- `leulit_meteo.checkwx_api_key`
- `leulit_meteo.aviation_weather_api_key` (opcional — API pública sin clave)

### Parámetros (`leulit.meteo.params`)

Controla el cron de actualización automática y las notificaciones de error. Parámetros del sistema escritos:

- `leulit_meteo.email_errores` — dirección(es) de correo para avisos de error del cron.
- Activa/desactiva el cron `cron_actualizar_metar_referencia` (cada 10 min por defecto).

El botón **Actualizar aeródromos de referencia** (en Parámetros) descarga desde aviationweather.gov (NOAA/FAA, sin API key) la lista de aeródromos españoles LE*/GC* con METAR o TAF y sincroniza la tabla `leulit.meteo.icao.reference`.

## Instalación abreviada

1. Instalar la dependencia Python `requests`.
2. Actualizar la lista de aplicaciones en Odoo e instalar **Leulit Meteorología**.
3. Configurar las API keys en `Meteorología → Configuración → API Keys`.
4. (Opcional) Activar el cron y configurar email de errores en `Meteorología → Configuración → Parámetros`.

Para el procedimiento detallado (Docker, permisos, validación de claves, troubleshooting) consulta [INSTALL.md](INSTALL.md).

## Documentación adicional

- [USAGE.md](USAGE.md) — Guía paso a paso de uso del módulo: creación de consultas, mapa interactivo, rutas, integración programática con otros módulos y ejemplos de código.
- [WORKFLOW.md](WORKFLOW.md) — Diagramas y flujo de datos entre vistas, modelos y APIs externas.
- [INTEGRACION_VUELO.md](INTEGRACION_VUELO.md) — Cómo vincular el METAR al parte de vuelo (`leulit_vuelo`).

## Compatibilidad

Odoo 17 Community. `__manifest__.py` declara `'version': '17.0.1.0.0'`.

Dependencias: `leulit`, `mail`. Dependencias externas Python: `requests`.

## Autor

**Leulit** — https://www.leulit.com

## Licencia

LGPL-3
