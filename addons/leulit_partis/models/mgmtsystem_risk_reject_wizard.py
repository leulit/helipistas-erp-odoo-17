"""Wizard para rechazar planes de tratamiento de riesgos."""

from odoo import fields, models, _


class MgmtSystemRiskRejectWizard(models.TransientModel):
    """Wizard para capturar motivo de rechazo de plan de tratamiento."""

    _name = "mgmtsystem.risk.reject.wizard"
    _description = "Rechazo de Plan de Tratamiento"

    risk_id = fields.Many2one(
        comodel_name="mgmtsystem.hazard",
        string="Riesgo",
        required=True,
    )
    rejection_reason = fields.Text(
        string="Motivo de Rechazo",
        required=True,
        help=_("Explique por qué se rechaza el plan de tratamiento."),
    )

    def action_confirm_rejection(self):
        """Confirma el rechazo del plan."""
        self.ensure_one()
        self.risk_id.write({
            "treatment_plan_state": "rejected",
            "treatment_plan_rejection_reason": self.rejection_reason,
        })
        return {"type": "ir.actions.act_window_close"}
