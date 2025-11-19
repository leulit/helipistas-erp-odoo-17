"""Extensión de activos para soportar PART-IS (SGSI) con base MAGERIT/PILAR."""

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


MAGERIT_SCALE = [
    ("1", "1 - Muy Bajo"),
    ("2", "2 - Bajo"),
    ("3", "3 - Medio"),
    ("4", "4 - Alto"),
    ("5", "5 - Muy Alto"),
]

ASSET_CRITICALITY = [
    ("negligible", "Nivel 0 - Residual"),
    ("low", "Nivel 1 - Bajo"),
    ("medium", "Nivel 2 - Medio"),
    ("high", "Nivel 3 - Alto"),
    ("critical", "Nivel 4 - Crítico"),
]

PILAR_REVIEW_INTERVAL = [
    ("3", "Trimestral"),
    ("6", "Semestral"),
    ("12", "Anual"),
]


class MgmtSystemAsset(models.Model):
    """Extiende mgmtsystem.hazard para gestionar Activos de Información según PART-IS/AESA-SGSI.
    
    Mapeo conceptual:
    - mgmtsystem.hazard (peligro) → Activo de Información SGSI
    - Añade valoración C-I-D según MAGERIT para cumplimiento PART-IS
    - Ciclo de revisión según normativa AESA
    """

    _inherit = "mgmtsystem.hazard"

    magerit_confidentiality = fields.Selection(
        selection=MAGERIT_SCALE,
        string="Confidencialidad PART-IS (SGSI)",
        default="3",
        help=_("Valoración de confidencialidad para el activo según PART-IS (basado en MAGERIT)."),
    )
    magerit_integrity = fields.Selection(
        selection=MAGERIT_SCALE,
        string="Integridad PART-IS (SGSI)",
        default="3",
        help=_("Valoración de integridad para el activo según PART-IS (basado en MAGERIT)."),
    )
    magerit_availability = fields.Selection(
        selection=MAGERIT_SCALE,
        string="Disponibilidad PART-IS (SGSI)",
        default="3",
        help=_("Valoración de disponibilidad para el activo según PART-IS (basado en MAGERIT)."),
    )
    magerit_asset_score = fields.Float(
        string="Índice PART-IS (SGSI)",
        compute="_compute_magerit_asset_profile",
        store=True,
        help=_("Puntuación promedio C-I-D empleada para priorizar análisis de riesgos."),
    )
    magerit_asset_level = fields.Selection(
        selection=ASSET_CRITICALITY,
        compute="_compute_magerit_asset_profile",
        store=True,
        string="Criticidad PART-IS (SGSI)",
        help=_("Clasificación automática de criticidad del activo."),
    )
    pilar_last_review_date = fields.Date(
        string="Última Revisión PART-IS (SGSI)",
        help=_("Fecha de la última revisión de controles del activo."),
    )
    pilar_review_interval = fields.Selection(
        selection=PILAR_REVIEW_INTERVAL,
        string="Periodicidad PART-IS (meses)",
        default="12",
        help=_("Frecuencia objetivo de revisión dentro del ciclo PART-IS (SGSI)."),
    )
    pilar_next_review_date = fields.Date(
        string="Próxima Revisión PART-IS (SGSI)",
        compute="_compute_pilar_next_review_date",
        store=True,
        help=_("Fecha planificada para la siguiente verificación del activo."),
    )

    @api.depends(
        "magerit_confidentiality",
        "magerit_integrity",
        "magerit_availability",
    )
    def _compute_magerit_asset_profile(self):
        """Calcula la media C-I-D y su traspaso a niveles PART-IS."""
        thresholds = self._get_asset_thresholds()
        for asset in self:
            scores = [
                asset._selection_to_int(asset.magerit_confidentiality),
                asset._selection_to_int(asset.magerit_integrity),
                asset._selection_to_int(asset.magerit_availability),
            ]
            valid_scores = [score for score in scores if score is not None]
            if not valid_scores:
                asset.magerit_asset_score = 0.0
                asset.magerit_asset_level = "negligible"
                continue
            average_score = sum(valid_scores) / len(valid_scores)
            asset.magerit_asset_score = average_score
            asset.magerit_asset_level = self._classify_asset_level(
                average_score, thresholds
            )

    @api.depends("pilar_last_review_date", "pilar_review_interval")
    def _compute_pilar_next_review_date(self):
        """Determina la fecha de próxima revisión en el ciclo PART-IS (SGSI)."""
        today = date.today()
        for asset in self:
            if asset.pilar_last_review_date and asset.pilar_review_interval:
                months = int(asset.pilar_review_interval)
                asset.pilar_next_review_date = asset.pilar_last_review_date + relativedelta(
                    months=months
                )
            elif asset.pilar_review_interval:
                months = int(asset.pilar_review_interval)
                asset.pilar_next_review_date = today + relativedelta(months=months)
            else:
                asset.pilar_next_review_date = False

    @staticmethod
    def _selection_to_int(value):
        """Convierte una selección de la escala PART-IS/MAGERIT a entero."""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @api.model
    def _get_asset_thresholds(self):
        """Recupera umbrales desde la configuración."""
        params = self.env["ir.config_parameter"].sudo()
        return {
            "low": self._float_param(
                params, "leulit_partis.asset_level_low", 1.5
            ),
            "medium": self._float_param(
                params, "leulit_partis.asset_level_medium", 2.5
            ),
            "high": self._float_param(
                params, "leulit_partis.asset_level_high", 3.5
            ),
            "critical": self._float_param(
                params, "leulit_partis.asset_level_critical", 4.5
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
    def _classify_asset_level(self, score, thresholds):
        """Traduce la puntuación media al nivel configurado."""
        if score >= thresholds["critical"]:
            return "critical"
        if score >= thresholds["high"]:
            return "high"
        if score >= thresholds["medium"]:
            return "medium"
        if score >= thresholds["low"]:
            return "low"
        return "negligible"
