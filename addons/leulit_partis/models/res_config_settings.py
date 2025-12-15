"""Configuraciones de MAGERIT y PILAR parametrizables."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    """Expone umbrales configurables para matrices MAGERIT/PILAR."""

    _inherit = "res.config.settings"

    magerit_asset_level_low = fields.Float(
        string="MAGERIT Activo - Bajo",
        default=1.5,
        config_parameter="leulit_partis.asset_level_low",
        help=_("Puntuación media C-I-D mínima para clasificar un activo como 'Bajo'."),
    )
    magerit_asset_level_medium = fields.Float(
        string="MAGERIT Activo - Medio",
        default=2.5,
        config_parameter="leulit_partis.asset_level_medium",
        help=_("Puntuación media C-I-D mínima para clasificar un activo como 'Medio'."),
    )
    magerit_asset_level_high = fields.Float(
        string="MAGERIT Activo - Alto",
        default=3.5,
        config_parameter="leulit_partis.asset_level_high",
        help=_("Puntuación media C-I-D mínima para clasificar un activo como 'Alto'."),
    )
    magerit_asset_level_critical = fields.Float(
        string="MAGERIT Activo - Crítico",
        default=4.5,
        config_parameter="leulit_partis.asset_level_critical",
        help=_("Puntuación media C-I-D mínima para clasificar un activo como 'Crítico'."),
    )

    magerit_risk_level_low = fields.Float(
        string="MAGERIT Riesgo - Bajo",
        default=3.0,
        config_parameter="leulit_partis.risk_level_low",
        help=_("Puntuación mínima Prob x Impacto para considerar un riesgo 'Bajo'."),
    )
    magerit_risk_level_medium = fields.Float(
        string="MAGERIT Riesgo - Medio",
        default=6.0,
        config_parameter="leulit_partis.risk_level_medium",
        help=_("Puntuación mínima Prob x Impacto para considerar un riesgo 'Medio'."),
    )
    magerit_risk_level_high = fields.Float(
        string="MAGERIT Riesgo - Alto",
        default=12.0,
        config_parameter="leulit_partis.risk_level_high",
        help=_("Puntuación mínima Prob x Impacto para considerar un riesgo 'Alto'."),
    )
    magerit_risk_level_critical = fields.Float(
        string="MAGERIT Riesgo - Crítico",
        default=20.0,
        config_parameter="leulit_partis.risk_level_critical",
        help=_("Puntuación mínima Prob x Impacto para considerar un riesgo 'Crítico'."),
    )

    @api.constrains(
        "magerit_asset_level_low",
        "magerit_asset_level_medium",
        "magerit_asset_level_high",
        "magerit_asset_level_critical",
    )
    def _check_asset_thresholds(self):
        for settings in self:
            if not settings._is_strictly_increasing(
                [
                    settings.magerit_asset_level_low,
                    settings.magerit_asset_level_medium,
                    settings.magerit_asset_level_high,
                    settings.magerit_asset_level_critical,
                ]
            ):
                raise ValidationError(
                    _("Los umbrales de activos deben ser crecientes de Bajo a Crítico."),
                )

    @api.constrains(
        "magerit_risk_level_low",
        "magerit_risk_level_medium",
        "magerit_risk_level_high",
        "magerit_risk_level_critical",
    )
    def _check_risk_thresholds(self):
        for settings in self:
            if not settings._is_strictly_increasing(
                [
                    settings.magerit_risk_level_low,
                    settings.magerit_risk_level_medium,
                    settings.magerit_risk_level_high,
                    settings.magerit_risk_level_critical,
                ]
            ):
                raise ValidationError(
                    _("Los umbrales de riesgo deben ser crecientes de Bajo a Crítico."),
                )

    @staticmethod
    def _is_strictly_increasing(values):
        """Valida lista estrictamente creciente."""
        filtered = [value for value in values if value is not None]
        return all(filtered[idx] < filtered[idx + 1] for idx in range(len(filtered) - 1))
