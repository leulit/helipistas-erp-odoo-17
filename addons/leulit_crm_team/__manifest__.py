# -*- coding: utf-8 -*-
{
    'name': 'Leulit CRM Team Security',
    'version': '17.0.1.1.0',
    'category': 'Sales/CRM',
    'summary': 'Reglas de seguridad por equipo de ventas para CRM',
    'description': """
        Añade un grupo de seguridad intermedio para CRM:
        - Usuario puede ver sus propios registros
        - Usuario puede ver registros de sus equipos de ventas
        - Usuario NO ve registros de otros equipos

        Además obliga a usar el botón "Perdido" para marcar leads como perdidos,
        garantizando que siempre se rellene el motivo y la nota de cierre.
    """,
    'author': 'Leulit',
    'depends': [
        'crm',           # Módulo CRM base
        'sale',          # Módulo de ventas
        'sales_team',    # Módulo de equipos de ventas
    ],
    'data': [
        'security/crm_security_groups.xml',
        'security/crm_security_rules.xml',
        # 'views/crm_stage_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    "license": "LGPL-3"
}
