# -*- coding: utf-8 -*-
{
    'name': 'Groups Manager - Visual Permission Management',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Modern and intuitive interface for managing user groups and permissions',
    'description': """
Groups Manager - Visual Permission Management
=============================================

Gestión visual y clara de grupos y permisos de usuarios en Odoo.

Características Principales:
----------------------------
* 🎯 Interfaz moderna y clara para gestión de grupos
* 👥 Vista de matriz Usuario × Grupo
* 🔗 Visualización de jerarquías de grupos (implied groups)
* 📊 Dashboard de permisos por usuario
* 🏷️ Organización por categorías/aplicaciones
* 🎨 Código de colores para identificación rápida
* ✅ Asignación múltiple de grupos de forma visual
* 📈 Análisis de cobertura de permisos

Ventajas sobre gestión tradicional:
------------------------------------
* Ver todos los grupos de un usuario de un vistazo
* Identificar rápidamente gaps en permisos
* Entender relaciones entre grupos
* Asignar múltiples roles sin complicaciones
* Auditoría visual de permisos

Casos de Uso:
-------------
* Usuario comercial que también es alumno
* Piloto que también hace funciones de instructor
* Personal con múltiples responsabilidades
* Auditoría de permisos y seguridad
    """,
    'author': 'Helipistas',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/res_groups_views.xml',
        'views/res_users_views.xml',
        'views/user_group_matrix_views.xml',
        'views/menu_diagnosis_wizard_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leulit_groups_manager/static/src/scss/groups_manager.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
