# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def write(self, vals):
        # Si se intenta archivar (marcar como perdido) sin motivo de pérdida, bloquearlo.
        # El botón "Perdido" del header envía lost_reason_id en el mismo write, por lo que
        # no se bloquea. La statusbar y el kanban no lo envían, por lo que sí se bloquean.
        if 'active' in vals and not vals['active']:
            for lead in self.filtered('active'):
                has_reason = vals.get('lost_reason_id') or lead.lost_reason_id
                if not has_reason:
                    raise UserError(_(
                        "Para marcar el lead «%s» como perdido debes usar el botón "
                        "«Perdido» del encabezado e indicar el motivo de pérdida y "
                        "la nota de cierre.",
                        lead.name,
                    ))
        return super().write(vals)
