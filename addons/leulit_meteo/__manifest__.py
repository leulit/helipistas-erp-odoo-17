# -*- coding: utf-8 -*-
{
    'name': 'Leulit Meteorología',
    'version': '17.0.1.0.0',
    'category': 'Operations',
    'summary': 'Integración con Open-Meteo para obtener datos meteorológicos',
    'description': """
        Módulo de integración con Open-Meteo y Aviation Weather APIs
        =============================================================
        
        Este módulo permite:
        * Consultar información meteorológica actual (Open-Meteo)
        * Obtener pronósticos meteorológicos hasta 16 días
        * Obtener reportes METAR aeronáuticos oficiales (Aviation Weather)
        * Integración con Windy API para modelos meteorológicos avanzados
        * Categorización automática de vuelo (VFR/MVFR/IFR/LIFR)
        * Almacenar histórico de consultas y reportes
        * Visualizar condiciones meteorológicas por ubicación o código OACI
        * Definir rutas (polilíneas) y obtener información meteorológica por punto
        * Widget de mapa interactivo para selección de ubicaciones
        * Integrar datos meteorológicos con operaciones de vuelo
        
        APIs:
        - Open-Meteo: https://open-meteo.com/
        - Windy: https://api.windy.com/
        - Aviation Weather: https://aviationweather.gov/
        
        IMPORTANTE: Los datos METAR son reportes históricos del momento
        de la consulta. Para obtener datos actuales, actualice el registro.
    """,
    'author': 'Leulit',
    'website': 'https://www.leulit.com',
    'license': 'LGPL-3',
    'depends': ['leulit', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/res_config_settings_views.xml',
        'views/leulit_meteo_ruta_template_views.xml',
        'views/leulit_meteo_consulta_views.xml',
        'views/leulit_meteo_metar_views.xml',
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
            # Widget JS
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
