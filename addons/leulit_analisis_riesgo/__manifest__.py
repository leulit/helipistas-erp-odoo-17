{
    'name': 'Leulit Análisis de Riesgo',
    'version': '17.0.1.0.0',
    'category': 'Project Management',
    'summary': 'Gestión y análisis de riesgos empresariales con exportación Excel',
    'description': '''
        Módulo para la gestión integral de análisis de riesgos que permite:
        - Crear estudios de análisis de riesgo con estructura de cabecera y líneas
        - Análisis de peligros y riesgos con clasificación automática
        - Evaluación de severidad y probabilidad (bruto y neto) por línea
        - Medidas de control y seguimiento individual
        - Estadísticas automáticas por análisis (riesgos altos/medios/bajos)
        - Creación automática de tareas de proyecto vinculadas
        - Exportación completa de datos a formato Excel formateado
        - Interfaz de edición tipo hoja de cálculo para líneas
        - Control de estados y seguimiento con mensajería integrada
    ''',
    'author': 'Leulit',
    'website': 'https://www.leulit.com',
    'depends': [
        'base',
        'project',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/riesgo_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}