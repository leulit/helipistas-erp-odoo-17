# -*- encoding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_open_source_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_("Esta actividad no tiene un documento fuente asociado."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
