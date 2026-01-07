"""Wizard para análisis masivo de riesgos sobre activos."""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MgmtSystemRiskBulkWizard(models.TransientModel):
    """Wizard para crear múltiples análisis de riesgo de forma masiva.
    
    Permite evaluar múltiples amenazas sobre uno o varios activos,
    facilitando el análisis sistemático requerido por PART-IS IS.D.OR.205.
    """

    _name = "mgmtsystem.risk.bulk.wizard"
    _description = "Análisis Masivo de Riesgos"

    asset_ids = fields.Many2many(
        comodel_name="mgmtsystem.hazard",
        string="Activos a Analizar",
        required=True,
        domain="[('magerit_threat_id', '=', False)]",
        help=_("Seleccione los activos sobre los que se realizará el análisis de riesgos."),
    )
    threat_ids = fields.Many2many(
        comodel_name="mgmtsystem.risk.threat",
        string="Amenazas a Evaluar",
        required=True,
        help=_("Seleccione las amenazas que se evaluarán contra los activos seleccionados."),
    )
    vulnerability_id = fields.Many2one(
        comodel_name="mgmtsystem.risk.vulnerability",
        string="Vulnerabilidad Común",
        help=_("Vulnerabilidad común a aplicar en todos los análisis (opcional)."),
    )
    default_strategy = fields.Selection(
        selection=[
            ("reduce", "Reducir"),
            ("avoid", "Evitar"),
            ("accept", "Aceptar"),
            ("transfer", "Transferir"),
        ],
        string="Estrategia por Defecto",
        help=_("Estrategia de tratamiento que se asignará a todos los riesgos creados."),
    )
    control_ids = fields.Many2many(
        comodel_name="mgmtsystem.risk.control",
        string="Controles por Defecto",
        help=_("Controles que se aplicarán a todos los riesgos creados (opcional)."),
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Departamento",
        required=True,
        help=_("Departamento responsable del análisis."),
    )
    responsible_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsable",
        required=True,
        default=lambda self: self.env.user,
        help=_("Usuario responsable del análisis de riesgos."),
    )
    analysis_date = fields.Date(
        string="Fecha de Análisis",
        required=True,
        default=fields.Date.today,
    )
    risk_count = fields.Integer(
        string="Riesgos a Crear",
        compute="_compute_risk_count",
        help=_("Número total de análisis de riesgo que se crearán (Activos × Amenazas)."),
    )

    @api.depends("asset_ids", "threat_ids")
    def _compute_risk_count(self):
        """Calcula cuántos riesgos se crearán."""
        for wizard in self:
            wizard.risk_count = len(wizard.asset_ids) * len(wizard.threat_ids)

    def action_create_risks(self):
        """Crea los análisis de riesgo de forma masiva."""
        self.ensure_one()
        
        if not self.asset_ids or not self.threat_ids:
            raise UserError(_("Debe seleccionar al menos un activo y una amenaza."))
        
        created_risks = self.env["mgmtsystem.hazard"]
        
        for asset in self.asset_ids:
            for threat in self.threat_ids:
                # Crear nombre descriptivo
                risk_name = _("%s - %s") % (asset.name, threat.name)
                
                # Preparar valores del riesgo
                vals = {
                    "name": risk_name,
                    "type_id": asset.type_id.id if asset.type_id else False,
                    "hazard_id": asset.hazard_id.id if asset.hazard_id else False,
                    "origin_id": asset.origin_id.id if asset.origin_id else False,
                    "department_id": self.department_id.id,
                    "responsible_user_id": self.responsible_user_id.id,
                    "analysis_date": self.analysis_date,
                    # Campos PART-IS
                    "magerit_asset_id": asset.id,
                    "magerit_threat_id": threat.id,
                    "magerit_vulnerability_id": self.vulnerability_id.id if self.vulnerability_id else False,
                    "magerit_probability": threat.default_probability or "3",
                    "magerit_impact": self._get_asset_impact_scale(asset),
                    "pilar_treatment_strategy": self.default_strategy,
                    "pilar_control_ids": [(6, 0, self.control_ids.ids)],
                }
                
                # Crear el riesgo
                risk = self.env["mgmtsystem.hazard"].create(vals)
                created_risks |= risk
        
        # Mostrar notificación y abrir vista de riesgos creados
        message = _("%s análisis de riesgo creados exitosamente.") % len(created_risks)
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Análisis Masivo Completado"),
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "name": _("Riesgos Creados"),
                    "res_model": "mgmtsystem.hazard",
                    "view_mode": "tree,form",
                    "domain": [("id", "in", created_risks.ids)],
                },
            },
        }

    @staticmethod
    def _get_asset_impact_scale(asset):
        """Convierte la valoración del activo en escala de impacto."""
        if not asset.magerit_asset_score:
            return "3"
        rounded = int(round(asset.magerit_asset_score))
        rounded = max(1, min(5, rounded))
        return str(rounded)


class MgmtSystemRiskBulkApplyControlsWizard(models.TransientModel):
    """Wizard para aplicar controles en lote a riesgos existentes."""

    _name = "mgmtsystem.risk.bulk.apply.controls.wizard"
    _description = "Aplicar Controles en Lote"

    risk_ids = fields.Many2many(
        comodel_name="mgmtsystem.hazard",
        string="Riesgos Seleccionados",
        required=True,
        domain="[('magerit_threat_id', '!=', False)]",
        help=_("Riesgos a los que se aplicarán los controles."),
    )
    control_ids = fields.Many2many(
        comodel_name="mgmtsystem.risk.control",
        string="Controles a Aplicar",
        required=True,
        help=_("Controles que se añadirán a los riesgos seleccionados."),
    )
    strategy = fields.Selection(
        selection=[
            ("reduce", "Reducir"),
            ("avoid", "Evitar"),
            ("accept", "Aceptar"),
            ("transfer", "Transferir"),
        ],
        string="Estrategia de Tratamiento",
        help=_("Actualizar la estrategia en todos los riesgos (opcional)."),
    )
    control_effectiveness = fields.Selection(
        selection=[
            ("0", "No Evaluado"),
            ("1", "Deficiente"),
            ("2", "Adecuado"),
            ("3", "Óptimo"),
        ],
        string="Eficacia de Controles",
        help=_("Evaluar la eficacia en todos los riesgos (opcional)."),
    )
    mode = fields.Selection(
        selection=[
            ("add", "Añadir a controles existentes"),
            ("replace", "Reemplazar controles existentes"),
        ],
        string="Modo de Aplicación",
        default="add",
        required=True,
    )

    def action_apply_controls(self):
        """Aplica los controles seleccionados a los riesgos."""
        self.ensure_one()
        
        if not self.risk_ids or not self.control_ids:
            raise UserError(_("Debe seleccionar riesgos y controles."))
        
        for risk in self.risk_ids:
            vals = {}
            
            # Actualizar controles según modo
            if self.mode == "replace":
                vals["pilar_control_ids"] = [(6, 0, self.control_ids.ids)]
            else:  # add
                current_controls = risk.pilar_control_ids.ids
                new_controls = list(set(current_controls + self.control_ids.ids))
                vals["pilar_control_ids"] = [(6, 0, new_controls)]
            
            # Actualizar estrategia si se especificó
            if self.strategy:
                vals["pilar_treatment_strategy"] = self.strategy
            
            # Actualizar eficacia si se especificó
            if self.control_effectiveness:
                vals["pilar_control_effectiveness"] = self.control_effectiveness
            
            risk.write(vals)
        
        message = _("Controles aplicados a %s riesgos.") % len(self.risk_ids)
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Controles Aplicados"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }
