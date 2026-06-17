# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

_LOST_MSG = _(
    "Para marcar el lead «%s» como perdido debes usar el botón "
    "«Perdido» del encabezado e indicar el motivo de pérdida y "
    "la nota de cierre."
)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    medium_id = fields.Many2one(required=True)

    def write(self, vals):
        # --- Caso 1: archivado directo (active=False) sin motivo ---
        if 'active' in vals and not vals['active']:
            for lead in self.filtered('active'):
                if not vals.get('lost_reason_id') and not lead.lost_reason_id:
                    raise UserError(_LOST_MSG % lead.name)

        # --- Caso 2: cambio de etapa a una etapa marcada como is_lost ---
        if 'stage_id' in vals and not vals.get('lost_reason_id'):
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            if new_stage.is_lost:
                for lead in self:
                    if not lead.lost_reason_id:
                        raise UserError(_LOST_MSG % lead.name)

        return super().write(vals)
