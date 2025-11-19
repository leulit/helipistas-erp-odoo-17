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


class MgmtSystemRisk(models.Model):
    """Extiende mgmtsystem.hazard.risk para análisis de riesgos SGSI según PART-IS/AESA.
    
    Mapeo conceptual:
    - mgmtsystem.hazard.risk (riesgo laboral) → Riesgo de Seguridad de la Información
    - Implementa metodología MAGERIT (amenaza × vulnerabilidad → activo)
    - Aplicación de controles según PILAR para cumplimiento PART-IS
    """

    _inherit = "mgmtsystem.hazard.risk"

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
