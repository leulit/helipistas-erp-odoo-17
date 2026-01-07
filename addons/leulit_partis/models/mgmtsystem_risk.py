"""Extensión del modelo de riesgo para PART-IS (SGSI)."""

from odoo import api, fields, models, _

from .mgmtsystem_asset import ASSET_CRITICALITY, MAGERIT_SCALE


PILAR_TREATMENT_STRATEGIES = [
    ("reduce", "Reducir"),
    ("avoid", "Evitar"),
    ("accept", "Aceptar"),
    ("transfer", "Transferir"),
]

PILAR_CONTROL_EFFECTIVENESS = [
    ("0", "No Evaluado"),
    ("1", "Deficiente"),
    ("2", "Adecuado"),
    ("3", "Óptimo"),
]

TREATMENT_PLAN_STATE = [
    ("draft", "Borrador"),
    ("pending", "Pendiente de Aprobación"),
    ("approved", "Aprobado"),
    ("implemented", "Implementado"),
    ("rejected", "Rechazado"),
]


class MgmtSystemRisk(models.Model):
    """Extiende mgmtsystem.hazard para análisis de riesgos SGSI según PART-IS/AESA.
    
    Mapeo conceptual:
    - mgmtsystem.hazard (OCA) se usa para representar ACTIVOS + RIESGOS
    - El módulo mgmtsystem_hazard_risk ya añade campos de cálculo de riesgo
    - Este archivo añade metodología MAGERIT (amenaza × vulnerabilidad → activo)
    - Aplicación de controles según PILAR para cumplimiento PART-IS
    
    Nota: Ambos mgmtsystem_asset.py y mgmtsystem_risk.py heredan de mgmtsystem.hazard.
    Esto es válido en Odoo - el ORM fusiona todas las extensiones del mismo modelo.
    """

    _inherit = "mgmtsystem.hazard"
    _description = "SGSI Risk Analysis (PART-IS/AESA)"

    magerit_asset_id = fields.Many2one(
        comodel_name="mgmtsystem.hazard",  # OCA base model para activos
        string="Activo Primario",
        help=_("Activo principal analizado en el escenario PART-IS (basado en MAGERIT)."),
    )
    magerit_threat_id = fields.Many2one(
        comodel_name="mgmtsystem.risk.threat",
        string="Amenaza PART-IS (SGSI)",
        help=_("Catálogo de amenazas conforme al marco PART-IS (basado en MAGERIT)."),
    )
    magerit_vulnerability_id = fields.Many2one(
        comodel_name="mgmtsystem.risk.vulnerability",
        string="Vulnerabilidad PART-IS (SGSI)",
        help=_("Catálogo de vulnerabilidades alineadas con PART-IS (SGSI)."),
    )
    magerit_probability = fields.Selection(
        selection=MAGERIT_SCALE,
        string="Probabilidad Intrínseca PART-IS",
        default="3",
        help=_("Probabilidad de ocurrencia siguiendo la escala PART-IS (derivada de MAGERIT)."),
    )
    magerit_impact = fields.Selection(
        selection=MAGERIT_SCALE,
        string="Impacto Intrínseco PART-IS",
        default="3",
        help=_("Impacto potencial considerando la valoración C-I-D del activo."),
    )
    magerit_inherent_score = fields.Integer(
        string="Riesgo Intrínseco PART-IS",
        compute="_compute_magerit_levels",
        store=True,
        help=_("Producto Probabilidad x Impacto en escala 1-25."),
    )
    magerit_inherent_level = fields.Selection(
        selection=ASSET_CRITICALITY,
        string="Nivel Intrínseco PART-IS",
        compute="_compute_magerit_levels",
        store=True,
        help=_("Categoría derivada del riesgo intrínseco."),
    )
    pilar_treatment_strategy = fields.Selection(
        selection=PILAR_TREATMENT_STRATEGIES,
        string="Estrategia PART-IS (SGSI)",
        help=_("Decisión de tratamiento conforme al marco PART-IS (SGSI)."),
    )
    pilar_control_ids = fields.Many2many(
        comodel_name="mgmtsystem.risk.control",
        relation="mgmtsystem_risk_pilar_control_rel",
        column1="risk_id",
        column2="control_id",
        string="Controles Asociados",
        help=_("Controles del catálogo PART-IS (SGSI) vinculados al tratamiento."),
    )
    pilar_control_summary = fields.Text(
        string="Controles Propuestos",
        help=_("Listado de controles implementados o planificados."),
    )
    pilar_control_effectiveness = fields.Selection(
        selection=PILAR_CONTROL_EFFECTIVENESS,
        string="Eficacia de Controles PART-IS",
        default="0",
        help=_("Resultado de la evaluación de eficacia de controles PART-IS."),
    )
    pilar_residual_probability = fields.Selection(
        selection=MAGERIT_SCALE,
        string="Probabilidad Residual PART-IS",
        default="3",
        help=_("Probabilidad tras la aplicación de controles."),
    )
    pilar_residual_impact = fields.Selection(
        selection=MAGERIT_SCALE,
        string="Impacto Residual PART-IS",
        default="3",
        help=_("Impacto residual tras la implantación de controles."),
    )
    pilar_residual_score = fields.Integer(
        string="Riesgo Residual PART-IS",
        compute="_compute_pilar_residual_level",
        store=True,
        help=_("Producto Probabilidad x Impacto residual."),
    )
    pilar_residual_level = fields.Selection(
        selection=ASSET_CRITICALITY,
        string="Nivel Residual PART-IS",
        compute="_compute_pilar_residual_level",
        store=True,
        help=_("Categoría derivada del riesgo residual."),
    )
    
    # Workflow de aprobación
    treatment_plan_state = fields.Selection(
        selection=TREATMENT_PLAN_STATE,
        string="Estado del Plan",
        default="draft",
        required=True,
        tracking=True,
        help=_("Estado del plan de tratamiento de riesgos según PART-IS IS.D.OR.210."),
    )
    treatment_plan_approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Aprobador",
        tracking=True,
        help=_("Responsable SGSI que aprueba el plan de tratamiento."),
    )
    treatment_plan_approval_date = fields.Datetime(
        string="Fecha de Aprobación",
        readonly=True,
        tracking=True,
    )
    treatment_plan_implementation_date = fields.Date(
        string="Fecha de Implementación",
        tracking=True,
        help=_("Fecha en que se implementaron los controles."),
    )
    treatment_plan_notes = fields.Text(
        string="Notas de Aprobación",
        help=_("Comentarios del aprobador o del responsable de implementación."),
    )
    treatment_plan_rejection_reason = fields.Text(
        string="Motivo de Rechazo",
        help=_("Explicación del rechazo del plan de tratamiento."),
    )

    @api.onchange("magerit_asset_id")
    def _onchange_magerit_asset_id(self):
        """Sincroniza impacto con el nivel del activo y limita vulnerabilidades."""
        for risk in self:
            if not risk.magerit_asset_id:
                continue
            scale_value = self._asset_score_to_scale(risk.magerit_asset_id.magerit_asset_score)
            if scale_value:
                risk.magerit_impact = scale_value

    @api.depends("magerit_probability", "magerit_impact")
    def _compute_magerit_levels(self):
        """Calcula puntuación y nivel intrínseco según PART-IS."""
        for risk in self:
            probability = self._selection_to_int(risk.magerit_probability)
            impact = self._selection_to_int(risk.magerit_impact)
            if probability is None or impact is None:
                risk.magerit_inherent_score = 0
                risk.magerit_inherent_level = "negligible"
                continue
            score = probability * impact
            risk.magerit_inherent_score = score
            risk.magerit_inherent_level = self._to_risk_level(score)

    @api.depends("pilar_residual_probability", "pilar_residual_impact")
    def _compute_pilar_residual_level(self):
        """Calcula riesgo residual tras aplicar controles PART-IS (SGSI)."""
        for risk in self:
            probability = self._selection_to_int(risk.pilar_residual_probability)
            impact = self._selection_to_int(risk.pilar_residual_impact)
            if probability is None or impact is None:
                risk.pilar_residual_score = 0
                risk.pilar_residual_level = "negligible"
                continue
            score = probability * impact
            risk.pilar_residual_score = score
            risk.pilar_residual_level = self._to_risk_level(score)

    @api.onchange("magerit_threat_id")
    def _onchange_magerit_threat_id(self):
        """Sincroniza probabilidad sugerida con la amenaza seleccionada."""
        for risk in self:
            if risk.magerit_threat_id and risk.magerit_threat_id.default_probability:
                risk.magerit_probability = risk.magerit_threat_id.default_probability

    @api.onchange("pilar_control_ids")
    def _onchange_pilar_control_ids(self):
        """Genera un resumen automático de controles seleccionados."""
        for risk in self:
            if risk.pilar_control_ids:
                lines = [
                    "[%s] %s" % (control.control_type.upper(), control.name)
                    if control.control_type
                    else control.name
                    for control in risk.pilar_control_ids
                ]
                risk.pilar_control_summary = "\n".join(lines)

    @staticmethod
    def _asset_score_to_scale(score):
        """Convierte la media C-I-D en escala entera PART-IS/MAGERIT."""
        if not score:
            return "3"
        rounded = int(round(score))
        rounded = max(1, min(5, rounded))
        return str(rounded)

    @staticmethod
    def _selection_to_int(value):
        """Convierte una selección en entero utilizable."""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @api.model
    def _get_risk_thresholds(self):
        """Recupera umbrales configurados para riesgos."""
        params = self.env["ir.config_parameter"].sudo()
        return {
            "low": self._float_param(
                params, "leulit_partis.risk_level_low", 3.0
            ),
            "medium": self._float_param(
                params, "leulit_partis.risk_level_medium", 6.0
            ),
            "high": self._float_param(
                params, "leulit_partis.risk_level_high", 12.0
            ),
            "critical": self._float_param(
                params, "leulit_partis.risk_level_critical", 20.0
            ),
        }

    @staticmethod
    def _float_param(params, key, default):
        """Convierte parámetros de configuración en float seguro."""
        try:
            return float(params.get_param(key, default))
        except (TypeError, ValueError):
            return default

    @api.model
    def _to_risk_level(self, score):
        """Xref de puntuación numérica a categorías configurables."""
        thresholds = self._get_risk_thresholds()
        if score >= thresholds["critical"]:
            return "critical"
        if score >= thresholds["high"]:
            return "high"
        if score >= thresholds["medium"]:
            return "medium"
        if score >= thresholds["low"]:
            return "low"
        return "negligible"

    # Métodos del workflow de aprobación
    def action_submit_for_approval(self):
        """Envía el plan de tratamiento para aprobación."""
        for risk in self:
            if not risk.pilar_treatment_strategy:
                raise models.ValidationError(
                    _("Debe definir una estrategia de tratamiento antes de solicitar aprobación.")
                )
            if not risk.pilar_control_ids and risk.pilar_treatment_strategy not in ["accept", "avoid"]:
                raise models.ValidationError(
                    _("Debe asociar controles al plan de tratamiento (excepto para 'Aceptar' o 'Evitar').")
                )
            risk.write({"treatment_plan_state": "pending"})
        return True

    def action_approve_treatment(self):
        """Aprueba el plan de tratamiento (solo responsable SGSI o manager)."""
        self.ensure_one()
        if not self.env.user.has_group("mgmtsystem.group_mgmtsystem_manager"):
            raise models.AccessError(
                _("Solo los responsables SGSI pueden aprobar planes de tratamiento.")
            )
        self.write({
            "treatment_plan_state": "approved",
            "treatment_plan_approver_id": self.env.user.id,
            "treatment_plan_approval_date": fields.Datetime.now(),
        })
        return True

    def action_reject_treatment(self):
        """Rechaza el plan de tratamiento."""
        self.ensure_one()
        if not self.env.user.has_group("mgmtsystem.group_mgmtsystem_manager"):
            raise models.AccessError(
                _("Solo los responsables SGSI pueden rechazar planes de tratamiento.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Rechazar Plan de Tratamiento",
            "res_model": "mgmtsystem.risk.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_risk_id": self.id},
        }

    def action_mark_implemented(self):
        """Marca el plan como implementado."""
        self.ensure_one()
        if self.treatment_plan_state != "approved":
            raise models.ValidationError(
                _("Solo se pueden marcar como implementados los planes aprobados.")
            )
        self.write({
            "treatment_plan_state": "implemented",
            "treatment_plan_implementation_date": fields.Date.today(),
        })
        return True

    def action_reset_to_draft(self):
        """Regresa el plan al estado de borrador."""
        for risk in self:
            risk.write({
                "treatment_plan_state": "draft",
                "treatment_plan_approver_id": False,
                "treatment_plan_approval_date": False,
                "treatment_plan_rejection_reason": False,
            })
        return True
