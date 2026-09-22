{
    'name': 'Leulit AI Search',
    'version': '0.3.2',
    'category': 'Extra Tools',
    'summary': 'AI-powered universal search across Odoo 18.0',
    'description': """
Leulit AI Search Addon for Odoo 18.0
===============================================
This Odoo add-on provides an AI-driven search bar that allows users to query
any data stored within their Odoo 18.0 instance using natural language.

Key Features:
- Natural language search across all modules
- Automatic model and field mapping
- Secure execution via ORM queries
- Configuration-based API key management
    """,
    'author': 'Leulit',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'images': ['static/description/cover.png', 'static/description/thumbnail.png'],
    'data': [
        'security/ir.model.access.csv',
        'views/settings_views.xml',
        'views/search_templates.xml',
        'views/ai_search_views.xml',
    ],
    # Assets definition for Odoo 18.0
    'assets': {
        'web.assets_backend': [
            # Component files - search page
            'leulit_ai/static/src/components/search_page/search_page.scss',
            'leulit_ai/static/src/components/search_page/search_page.js',
            'leulit_ai/static/src/components/search_page/search_page.xml',

            # Report dialog component
            'leulit_ai/static/src/components/report_dialog/report_dialog.js',
            'leulit_ai/static/src/components/report_dialog/report_dialog.xml',

            # Report visualization component
            'leulit_ai/static/src/components/report_visualization/report_visualization.js',
            'leulit_ai/static/src/components/report_visualization/report_visualization.xml',

            # Search menu - adds systray button
            'leulit_ai/static/src/js/search_menu.js',
            'leulit_ai/static/src/js/search_menu.xml',
            'leulit_ai/static/src/js/search_menu.scss',

            # Action registry - registers client action
            'leulit_ai/static/src/js/action_registry.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
