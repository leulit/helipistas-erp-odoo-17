# Copyright 2025
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Leulit PART-IS",
    "summary": "Sistema de Gestión de Seguridad de la Información (SGSI) para compañías aéreas - EASA PART-IS y AESA",
    "version": "17.0.1.0.0",
    "author": "Leulit, Odoo Community Association (OCA)",
    "website": "https://leulit.com",
    "category": "Operations/Management System",
    "license": "AGPL-3",
    "depends": [
        "mgmtsystem",              # Base OCA para sistemas de gestión
        "mgmtsystem_hazard",       # Usado para modelar activos de información
        "mgmtsystem_hazard_risk",  # Usado para análisis de riesgos SGSI
        "mgmtsystem_manual",       # Para documentación del SGSI
        "document_page",           # Para manuales, políticas y procedimientos
        "hr",                      # Para departamentos y responsables
    ],
    "external_dependencies": {
        "python": ["dateutil"],
    },
    "data": [
        "security/ir_model_access.xml",
        "security/mgmtsystem_risk_rules.xml",
        "views/mgmtsystem_asset_views.xml",
        "views/mgmtsystem_risk_views.xml",
        "views/mgmtsystem_catalog_views.xml",
        "views/mgmtsystem_document_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_hook",
}
