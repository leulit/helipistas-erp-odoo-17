# -*- coding: utf-8 -*-
{
    'name': 'Leulit Meteorología',
    'version': '17.0.1.0.0',
    'category': 'Operations',
    'summary': 'Consultas meteorológicas (Open-Meteo, Windy) y METAR sintético desde AEMET OpenData',
    'description': """
        Leulit Meteorología
        ===================

        Módulo de consultas meteorológicas para operaciones de vuelo, integrado con
        APIs públicas y con un widget de mapa interactivo basado en Leaflet (OWL).

        Funcionalidades principales:
        * Consulta de clima actual y pronósticos con Open-Meteo (sin clave).
        * Capas y modelos meteorológicos avanzados con Windy (REST + embed).
        * METAR sintético generado a partir de observaciones de AEMET OpenData
          (texto tipo METAR con sufijo ``RMK AEMET``; AEMET no publica METAR oficiales).
        * Definición de rutas como polilíneas (waypoints) y consulta meteo por punto.
        * Plantillas de ruta reutilizables.
        * Widget de mapa interactivo (Leaflet + componente OWL) para selección de
          ubicaciones y visualización de la polilínea.
        * Histórico de consultas y reportes con secuencias propias.

        Arquitectura de proveedores METAR:
        * Modelo único ``leulit.meteo.metar`` con campo ``provider``.
        * Interfaz ``MetarProvider`` con registro vía decorador ``@register_provider``.
        * Cliente HTTP por proveedor (hoy: ``AemetOpenDataService``).
        * Para añadir nuevos proveedores basta con registrar una subclase de
          ``MetarProvider`` en ``models/`` antes de importar ``leulit_meteo_metar``.

        APIs externas:
        * Open-Meteo: https://open-meteo.com/ (sin clave)
        * Windy: https://api.windy.com/ (clave opcional para REST; embed sin clave)
        * AEMET OpenData: https://opendata.aemet.es/ (requiere clave JWT)
    """,
    'author': 'Leulit',
    'website': 'https://www.leulit.com',
    'license': 'LGPL-3',
    'depends': ['leulit', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/leulit_meteo_ruta_template_views.xml',
        'views/leulit_meteo_consulta_views.xml',
        'views/leulit_meteo_metar_views.xml',
        'views/leulit_meteo_config_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Leaflet CSS (CDN)
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
            # Widget CSS
            'leulit_meteo/static/src/css/meteo_map_widget.css',
            # Leaflet JS (CDN)
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            # Widget JS (OWL Component)
            'leulit_meteo/static/src/js/meteo_map_widget.js',
            # Widget Templates
            'leulit_meteo/static/src/xml/meteo_map_widget.xml',
        ],
    },
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
