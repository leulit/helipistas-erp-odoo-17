"""Extiende document.page para generar documentación SGSI según PART-IS/AESA."""

from odoo import api, fields, models, _


class DocumentPage(models.Model):
    """Extiende document.page para documentación del SGSI conforme a PART-IS/AESA.
    
    Permite generar y mantener:
    - Manual SGSI
    - Política de Seguridad de la Información
    - Procedimientos de seguridad
    - Registros de análisis de riesgos
    - Documentación de controles implementados
    
    Proporciona trazabilidad con activos, riesgos y controles para auditorías EASA/AESA.
    """

    _inherit = "document.page"

    is_part_is_manual = fields.Boolean(
        string="Documento SGSI PART-IS",
        help=_(
            "Marca este documento como parte del Sistema de Gestión de Seguridad"
            " de la Información requerido por EASA PART-IS y AESA."
        ),
    )
    partis_document_type = fields.Selection(
        selection=[
            ("sgsi_manual", "Manual SGSI"),
            ("security_policy", "Política de Seguridad"),
            ("procedure", "Procedimiento"),
            ("risk_register", "Registro de Riesgos"),
            ("control_catalog", "Catálogo de Controles"),
            ("audit_report", "Informe de Auditoría"),
            ("other", "Otro"),
        ],
        string="Tipo Documento PART-IS",
        help=_("Clasificación del documento según requisitos PART-IS/AESA."),
    )
    linked_asset_ids = fields.Many2many(
        comodel_name="mgmtsystem.hazard",  # OCA base model
        relation="document_page_asset_rel",
        column1="document_id",
        column2="asset_id",
        string="Activos Relacionados",
        help=_("Activos de información referenciados en este documento."),
    )
    linked_risk_ids = fields.Many2many(
        comodel_name="mgmtsystem.hazard",  # OCA base model (usado para activos Y riesgos)
        relation="document_page_risk_rel",
        column1="document_id",
        column2="risk_id",
        string="Riesgos Referenciados",
        help=_("Riesgos SGSI analizados e incluidos en la documentación."),
    )
    linked_control_ids = fields.Many2many(
        comodel_name="mgmtsystem.risk.control",
        relation="document_page_control_rel",
        column1="document_id",
        column2="control_id",
        string="Controles Asociados",
        help=_("Controles aplicados que se documentan para cumplimiento PART-IS."),
    )
    next_pilar_review_date = fields.Date(
        string="Próxima Revisión PART-IS",
        compute="_compute_next_pilar_review_date",
        store=True,
        help=_(
            "Fecha más próxima de revisión entre los activos referenciados (ciclo SGSI)."
        ),
    )
    control_overview = fields.Text(
        string="Resumen de Controles",
        compute="_compute_control_overview",
        store=True,
        help=_("Listado de controles vinculados para auditorías."),
    )

    @api.depends("linked_asset_ids.pilar_next_review_date")
    def _compute_next_pilar_review_date(self):
        """Calcula la fecha de revisión más próxima entre activos asociados."""
        for document in self:
            dates = document.mapped("linked_asset_ids.pilar_next_review_date")
            document.next_pilar_review_date = (
                min(dates) if dates else False
            )

    @api.depends("linked_control_ids", "linked_control_ids.control_type")
    def _compute_control_overview(self):
        """Compone un resumen textual de los controles enlazados."""
        for document in self:
            if not document.linked_control_ids:
                document.control_overview = False
                continue
            lines = [
                "[%s] %s"
                % (
                    control.control_type.upper(),
                    control.name,
                )
                if control.control_type
                else control.name
                for control in document.linked_control_ids
            ]
            document.control_overview = "\n".join(lines)
