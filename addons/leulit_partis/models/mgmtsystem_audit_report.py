"""Reportes y análisis de auditoría SGSI."""

from datetime import datetime, timedelta

from odoo import api, fields, models, _


class MgmtSystemAuditReport(models.Model):
    """Reporte de auditoría consolidado para SGSI PART-IS.
    
    Facilita el análisis de accesos y cambios en información crítica
    para cumplimiento de IS.D.OR.305 (Mejora continua y auditorías).
    """

    _name = "mgmtsystem.audit.report"
    _description = "SGSI Audit Report"
    _order = "date_from desc"

    name = fields.Char(
        string="Nombre del Reporte",
        required=True,
        default="Reporte de Auditoría SGSI",
    )
    date_from = fields.Date(
        string="Fecha Desde",
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30),
    )
    date_to = fields.Date(
        string="Fecha Hasta",
        required=True,
        default=fields.Date.today,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Usuarios",
        help=_("Filtrar por usuarios específicos (dejar vacío para todos)."),
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Modelo",
        help=_("Filtrar por modelo específico (dejar vacío para todos)."),
    )
    log_count = fields.Integer(
        string="Total de Registros",
        compute="_compute_audit_stats",
        store=False,
    )
    read_count = fields.Integer(
        string="Lecturas",
        compute="_compute_audit_stats",
        store=False,
    )
    create_count = fields.Integer(
        string="Creaciones",
        compute="_compute_audit_stats",
        store=False,
    )
    write_count = fields.Integer(
        string="Modificaciones",
        compute="_compute_audit_stats",
        store=False,
    )
    unlink_count = fields.Integer(
        string="Eliminaciones",
        compute="_compute_audit_stats",
        store=False,
    )
    critical_changes_count = fields.Integer(
        string="Cambios Críticos",
        compute="_compute_audit_stats",
        store=False,
        help=_("Cambios en campos críticos: estado de planes, niveles de riesgo, aprobaciones."),
    )

    @api.depends("date_from", "date_to", "user_ids", "model_id")
    def _compute_audit_stats(self):
        """Calcula estadísticas de auditoría."""
        for report in self:
            domain = report._get_audit_domain()
            
            logs = self.env["auditlog.log"].search(domain)
            
            report.log_count = len(logs)
            report.read_count = len(logs.filtered(lambda l: l.method == "read"))
            report.create_count = len(logs.filtered(lambda l: l.method == "create"))
            report.write_count = len(logs.filtered(lambda l: l.method == "write"))
            report.unlink_count = len(logs.filtered(lambda l: l.method == "unlink"))
            
            # Contar cambios críticos
            critical_fields = [
                "treatment_plan_state",
                "treatment_plan_approver_id",
                "magerit_asset_level",
                "pilar_residual_level",
                "pilar_treatment_strategy",
            ]
            
            critical_count = 0
            for log in logs.filtered(lambda l: l.method == "write"):
                for line in log.line_ids:
                    if line.field_id.name in critical_fields:
                        critical_count += 1
                        break
            
            report.critical_changes_count = critical_count

    def _get_audit_domain(self):
        """Construye el dominio de búsqueda para auditlog."""
        self.ensure_one()
        
        domain = [
            ("create_date", ">=", fields.Datetime.to_datetime(self.date_from)),
            ("create_date", "<=", fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)),
        ]
        
        if self.user_ids:
            domain.append(("user_id", "in", self.user_ids.ids))
        
        if self.model_id:
            domain.append(("model_id", "=", self.model_id.id))
        
        return domain

    def action_view_audit_logs(self):
        """Abre la vista de logs de auditoría filtrados."""
        self.ensure_one()
        
        return {
            "type": "ir.actions.act_window",
            "name": _("Registros de Auditoría"),
            "res_model": "auditlog.log",
            "view_mode": "tree,form",
            "domain": self._get_audit_domain(),
            "context": {"create": False},
        }

    def action_view_critical_changes(self):
        """Abre la vista de cambios críticos."""
        self.ensure_one()
        
        domain = self._get_audit_domain() + [("method", "=", "write")]
        
        # Filtrar logs que tengan cambios en campos críticos
        critical_fields = [
            "treatment_plan_state",
            "treatment_plan_approver_id",
            "magerit_asset_level",
            "pilar_residual_level",
            "pilar_treatment_strategy",
        ]
        
        all_logs = self.env["auditlog.log"].search(domain)
        critical_log_ids = []
        
        for log in all_logs:
            for line in log.line_ids:
                if line.field_id.name in critical_fields:
                    critical_log_ids.append(log.id)
                    break
        
        return {
            "type": "ir.actions.act_window",
            "name": _("Cambios Críticos"),
            "res_model": "auditlog.log",
            "view_mode": "tree,form",
            "domain": [("id", "in", critical_log_ids)],
            "context": {"create": False},
        }

    def action_generate_report(self):
        """Genera y muestra el reporte de auditoría."""
        self.ensure_one()
        
        # Recalcular estadísticas
        self._compute_audit_stats()
        
        return {
            "type": "ir.actions.act_window",
            "name": _("Reporte de Auditoría SGSI"),
            "res_model": "mgmtsystem.audit.report",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }
