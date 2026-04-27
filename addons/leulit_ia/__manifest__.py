# -*- coding: utf-8 -*-
{
    'name': 'Leulit IA Assistant',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Asistente IA integrado en Odoo via Function Calling (Claude / Ollama)',
    'author': 'Leulit',
    'website': 'https://www.leulit.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'leulit_ia/static/src/components/AiChatSidebar/AiChatSidebar.scss',
            'leulit_ia/static/src/components/AiChatSidebar/AiChatSidebar.js',
            'leulit_ia/static/src/components/AiChatSidebar/AiChatSidebar.xml',
        ],
    },
    'external_dependencies': {
        'python': ['anthropic', 'requests'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
