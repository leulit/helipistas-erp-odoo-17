# -*- coding: utf-8 -*-
"""
Leulit Meteorología - Documentación del Módulo
===============================================

Módulo de consultas meteorológicas para Odoo 17 Community, orientado a
operaciones de vuelo. Integra Open-Meteo, Windy y AEMET OpenData, e incluye
un widget de mapa interactivo basado en Leaflet (OWL).

Autor: Leulit
Versión: 17.0.1.0.0
Licencia: LGPL-3

Modelos
-------
leulit.meteo.consulta
    Consulta meteorológica puntual o sobre polilínea.
    Soporta Open-Meteo y Windy. Secuencia ``METEO-XXXXX``.

leulit.meteo.consulta.punto
    Waypoint de la polilínea asociada a una consulta.

leulit.meteo.ruta.template
    Plantilla de ruta reutilizable (lista de waypoints).

leulit.meteo.ruta.template.punto
    Waypoint de una plantilla de ruta.

leulit.meteo.metar
    Reporte tipo METAR. Campo ``provider`` (Selection) identifica el origen.
    Hoy el único proveedor activo es ``aemet``. Secuencia ``METAR-XXXXX``.

res.config.settings (extendido)
    Claves de configuración: ``windy_api_key``, ``windy_model``,
    ``aemet_api_key``.

Servicios HTTP (``models/*_service.py``)
----------------------------------------
OpenMeteoService
    Cliente para https://open-meteo.com/ (sin autenticación).

WindyService
    Cliente para Windy REST. La clave es opcional; el embed funciona sin clave.

AemetOpenDataService
    Cliente para AEMET OpenData (JWT). AEMET **no publica METAR oficiales**;
    el módulo sintetiza un texto tipo METAR a partir de las observaciones
    horarias y le añade el sufijo ``RMK AEMET`` para dejarlo claro.

Arquitectura de proveedores METAR
---------------------------------
Capa 1 (modelo)
    ``leulit.meteo.metar`` con campo Selection ``provider`` (default ``'aemet'``).

Capa 2 (proveedores)
    Interfaz ``MetarProvider`` definida en
    ``models/leulit_meteo_metar_provider.py`` y registro mediante el decorador
    ``@register_provider``. Implementación actual:
    ``AemetMetarProvider`` (``code='aemet'``) en
    ``models/leulit_meteo_metar_aemet.py``.

Capa 3 (cliente HTTP)
    ``AemetOpenDataService``.

Cómo añadir un nuevo proveedor
    1. Crear ``models/leulit_meteo_metar_<proveedor>.py`` con una subclase de
       ``MetarProvider`` decorada con ``@register_provider``.
    2. Importarlo en ``models/__init__.py`` **antes** de
       ``leulit_meteo_metar`` para que el registro esté listo cuando el
       Selection del modelo se construya.
    3. Añadir la clave correspondiente en ``res.config.settings`` si requiere
       autenticación.

Vistas y menú
-------------
- ``views/leulit_meteo_consulta_views.xml``
- ``views/leulit_meteo_ruta_template_views.xml``
- ``views/leulit_meteo_metar_views.xml``
- ``views/res_config_settings_views.xml``
- ``views/menu.xml``

Datos
-----
- ``data/sequences.xml``: secuencias ``METEO-`` y ``METAR-``.

Seguridad
---------
``security/ir.model.access.csv`` con accesos para los 5 modelos de aplicación
(consulta, consulta.punto, ruta.template, ruta.template.punto, metar) sobre
los grupos ``leulit.RBase`` y ``leulit.RBase_employee``.

Assets web (backend)
--------------------
- Leaflet 1.9.4 CSS/JS desde unpkg.com (CDN).
- ``static/src/css/meteo_map_widget.css``
- ``static/src/js/meteo_map_widget.js`` — componente OWL.
- ``static/src/xml/meteo_map_widget.xml`` — plantillas OWL.

APIs externas
-------------
- Open-Meteo: https://open-meteo.com/  (sin clave)
- Windy: https://api.windy.com/         (clave opcional para REST; embed libre)
- AEMET OpenData: https://opendata.aemet.es/  (clave JWT)

Dependencias
------------
Odoo:
- ``leulit`` (módulo base)
- ``mail`` (chatter / tracking)

Python:
- ``requests``

Configuración
-------------
Ajustes → Leulit Meteorología:
- ``windy_api_key``: clave de Windy (opcional para REST; embed funciona sin ella).
- ``windy_model``: modelo Windy a usar.
- ``aemet_api_key``: token JWT de AEMET OpenData.
"""

__version__ = '17.0.1.0.0'
__author__ = 'Leulit'
__license__ = 'LGPL-3'
