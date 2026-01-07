"""Dashboard y KPIs para SGSI PART-IS."""

from odoo import api, fields, models


class MgmtSystemDashboard(models.Model):
    """Dashboard SGSI PART-IS con KPIs e indicadores de cumplimiento.
    
    IS.D.OR.305 - Mejora continua: métricas y seguimiento del SGSI.
    """

    _name = "mgmtsystem.dashboard"
    _description = "SGSI Dashboard (PART-IS)"

    name = fields.Char(
        string="Nombre del Dashboard",
        required=True,
        default="Dashboard SGSI PART-IS",
    )
    date = fields.Date(
        string="Fecha",
        default=fields.Date.today,
        required=True,
    )
    
    # KPIs de Activos
    total_assets = fields.Integer(
        string="Total Activos",
        compute="_compute_asset_kpis",
        store=False,
    )
    critical_assets = fields.Integer(
        string="Activos Críticos",
        compute="_compute_asset_kpis",
        store=False,
    )
    high_assets = fields.Integer(
        string="Activos Alto",
        compute="_compute_asset_kpis",
        store=False,
    )
    assets_review_pending = fields.Integer(
        string="Revisiones Pendientes (Activos)",
        compute="_compute_asset_kpis",
        store=False,
    )
    
    # KPIs de Riesgos
    total_risks = fields.Integer(
        string="Total Riesgos",
        compute="_compute_risk_kpis",
        store=False,
    )
    critical_inherent_risks = fields.Integer(
        string="Riesgos Intrínsecos Críticos",
        compute="_compute_risk_kpis",
        store=False,
    )
    critical_residual_risks = fields.Integer(
        string="Riesgos Residuales Críticos",
        compute="_compute_risk_kpis",
        store=False,
    )
    untreated_risks = fields.Integer(
        string="Riesgos Sin Tratar",
        compute="_compute_risk_kpis",
        store=False,
        help="Riesgos sin estrategia de tratamiento o sin controles aplicados",
    )
    
    # KPIs de Tratamiento
    total_controls = fields.Integer(
        string="Total Controles",
        compute="_compute_control_kpis",
        store=False,
    )
    active_controls = fields.Integer(
        string="Controles Activos",
        compute="_compute_control_kpis",
        store=False,
    )
    
    # KPI de Cumplimiento
    compliance_rate = fields.Float(
        string="Nivel de Cumplimiento (%)",
        compute="_compute_compliance_rate",
        store=False,
        help="Porcentaje basado en activos valorados, riesgos analizados y tratados",
    )

    @api.depends("date")
    def _compute_asset_kpis(self):
        """Calcula KPIs de activos de información."""
        for rec in self:
            # Activos sin amenaza (magerit_threat_id = False)
            assets = self.env["mgmtsystem.hazard"].search(
                [("magerit_threat_id", "=", False)]
            )
            
            rec.total_assets = len(assets)
            rec.critical_assets = len(
                assets.filtered(lambda a: a.magerit_asset_level == "critical")
            )
            rec.high_assets = len(
                assets.filtered(lambda a: a.magerit_asset_level == "high")
            )
            
            # Activos con revisión pendiente (fecha de revisión <= hoy)
            today = fields.Date.today()
            rec.assets_review_pending = len(
                assets.filtered(
                    lambda a: a.pilar_next_review_date 
                    and a.pilar_next_review_date <= today
                )
            )

    @api.depends("date")
    def _compute_risk_kpis(self):
        """Calcula KPIs de análisis de riesgos."""
        for rec in self:
            # Riesgos con amenaza (magerit_threat_id != False)
            risks = self.env["mgmtsystem.hazard"].search(
                [("magerit_threat_id", "!=", False)]
            )
            
            rec.total_risks = len(risks)
            rec.critical_inherent_risks = len(
                risks.filtered(lambda r: r.magerit_inherent_level == "critical")
            )
            rec.critical_residual_risks = len(
                risks.filtered(lambda r: r.pilar_residual_level == "critical")
            )
            
            # Riesgos sin tratar: sin estrategia o sin controles
            rec.untreated_risks = len(
                risks.filtered(
                    lambda r: not r.pilar_treatment_strategy 
                    or not r.pilar_control_ids
                )
            )

    @api.depends("date")
    def _compute_control_kpis(self):
        """Calcula KPIs de controles."""
        for rec in self:
            controls = self.env["mgmtsystem.risk.control"].search([])
            rec.total_controls = len(controls)
            rec.active_controls = len(controls.filtered(lambda c: c.active))

    @api.depends(
        "total_assets",
        "critical_assets",
        "total_risks",
        "untreated_risks",
    )
    def _compute_compliance_rate(self):
        """Calcula nivel de cumplimiento SGSI.
        
        Criterios:
        - 25% Activos críticos identificados y valorados
        - 25% Riesgos analizados
        - 50% Riesgos tratados (con estrategia y controles)
        """
        for rec in self:
            compliance = 0.0
            
            # 25% por activos críticos valorados
            if rec.total_assets > 0:
                compliance += 25.0
            
            # 25% por riesgos analizados
            if rec.total_risks > 0:
                compliance += 25.0
            
            # 50% por riesgos tratados
            if rec.total_risks > 0:
                treated_risks = rec.total_risks - rec.untreated_risks
                compliance += (treated_risks / rec.total_risks) * 50.0
            
            rec.compliance_rate = min(compliance, 100.0)

    def action_view_assets(self):
        """Abre la vista de activos de información."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Activos de Información",
            "res_model": "mgmtsystem.hazard",
            "view_mode": "tree,form",
            "domain": [("magerit_threat_id", "=", False)],
            "context": {"create": True},
        }

    def action_view_risks(self):
        """Abre la vista de análisis de riesgos."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Análisis de Riesgos",
            "res_model": "mgmtsystem.hazard",
            "view_mode": "tree,form",
            "domain": [("magerit_threat_id", "!=", False)],
            "context": {"create": True},
        }
