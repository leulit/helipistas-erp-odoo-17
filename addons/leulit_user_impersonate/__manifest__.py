# -*- coding: utf-8 -*-
{
    'name': 'User Impersonation',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Allow administrators to impersonate users for testing and auditing',
    'description': """
User Impersonation for Odoo 17
===============================

Features:
---------
* Impersonate any user to see Odoo from their perspective
* Visual banner showing when you're impersonating
* Easy switch back to your original user
* Security: only authorized users can impersonate
* Audit trail of impersonation sessions
* Menu analysis to visualize user permissions

Use Cases:
----------
* Test user permissions and access rights
* Debug user-specific issues
* Audit what users can see and do
* Training and support scenarios
    """,
    'author': 'Helipistas',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/user_menu_analysis_views.xml',
        'views/res_users_views.xml',
        'views/impersonate_banner.xml',
        'security/user_menu_analysis_security.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leulit_user_impersonate/static/src/js/impersonate_banner.js',
            'leulit_user_impersonate/static/src/xml/impersonate_banner.xml',
            'leulit_user_impersonate/static/src/scss/impersonate_banner.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
