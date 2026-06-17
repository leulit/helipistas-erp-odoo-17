# -*- encoding: utf-8 -*-
from odoo import _, fields, models


class LeuilitWizardCerrarNC(models.TransientModel):
    _name = "leulit.wizard.cerrar.nc"
    _description = "Cerrar No Conformidad"

    nc_id = fields.Many2one(
        "mgmtsystem.nonconformity",
        string="No Conformidad",
        required=True,
        readonly=True,
    )
    immediate_action_id = fields.Many2one(
        "mgmtsystem.action",
        string="Acción Inmediata",
        required=True,
    )
    motivo_cierre = fields.Text(
        string="Motivo de Cierre",
        required=True,
    )

    def action_confirmar_cierre(self):
        self.ensure_one()
        stage_done = self.env.ref("mgmtsystem_nonconformity.stage_done")
        self.nc_id.write({
            "immediate_action_id": self.immediate_action_id.id,
            "motivo_cierre": self.motivo_cierre,
            "stage_id": stage_done.id,
        })
        return {"type": "ir.actions.act_window_close"}
