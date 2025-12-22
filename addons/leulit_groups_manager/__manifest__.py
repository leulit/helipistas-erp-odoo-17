# -*- coding: utf-8 -*-
{
    'name': 'Groups Manager - Visual Permission Management',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Modern and intuitive interface for managing user groups and permissions',
    'description': """
Groups Manager - Visual Permission Management
=============================================



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
        'security/ir_model_access.xml',
        'views/group_copy_wizard_views.xml',  # Debe estar antes de res_groups_views.xml
        'views/res_groups_views.xml',
        'views/res_users_views.xml',
        'views/user_group_matrix_views.xml',
        'views/menu_diagnosis_wizard_views.xml',
        'views/menu_list_wizard_views.xml',
        'security/wizards_access.xml',
        'views/menu_diagnosis_action.xml',  # Debe estar antes de menu.xml
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
