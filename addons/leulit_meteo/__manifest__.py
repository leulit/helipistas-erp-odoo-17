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
        * Categorización automática de vuelo (VFR/MVFR/IFR/LIFR)
        * Almacenar histórico de consultas y reportes
        * Visualizar condiciones meteorológicas por ubicación o código OACI
        * Integrar datos meteorológicos con operaciones de vuelo
        
        APIs:
        - Open-Meteo: https://open-meteo.com/
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
        'views/leulit_meteo_consulta_views.xml',
        'views/leulit_meteo_metar_views.xml',
        'views/menu.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
