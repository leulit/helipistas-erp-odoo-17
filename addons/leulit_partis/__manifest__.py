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
    "images": ["static/description/icon.png"],
    "depends": [
        "mgmtsystem",              # Base OCA para sistemas de gestión
        "mgmtsystem_hazard",       # Usado para modelar activos de información
        "mgmtsystem_hazard_risk",  # Usado para análisis de riesgos SGSI
        "mgmtsystem_manual",       # Para documentación del SGSI
        "document_page",           # Para manuales, políticas y procedimientos
        "hr",                      # Para departamentos y responsables
        "auditlog",                # OCA: Auditoría de cambios en registros críticos
    ],
    "external_dependencies": {
        "python": ["dateutil"],
    },
    "data": [
        # Vistas primero (registran modelos)
        "views/mgmtsystem_dashboard_views.xml",
        "views/mgmtsystem_asset_views.xml",
        "views/mgmtsystem_risk_views.xml",
        "views/mgmtsystem_risk_reject_wizard_views.xml",
        "views/mgmtsystem_risk_bulk_wizard_views.xml",
        "views/mgmtsystem_risk_export_wizard_views.xml",
        "views/mgmtsystem_catalog_views.xml",
        "views/mgmtsystem_document_views.xml",
        "views/mgmtsystem_audit_views.xml",
        "views/res_config_settings_views.xml",
        "report/risk_treatment_plan_report.xml",
        "report/risk_treatment_plan_template.xml",
        # Seguridad después de las vistas
        "security/ir_model_access.xml",
        "security/mgmtsystem_risk_rules.xml",
        # Datos al final
        "data/auditlog_rules.xml",
        "data/notification_templates.xml",
        "data/cron_jobs.xml",
    ],
    "installable": True,
    "application": True,
    "post_init_hook": "post_init_hook",
}
