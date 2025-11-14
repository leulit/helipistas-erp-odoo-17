# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime


import logging
_logger = logging.getLogger(__name__)

class MailActivity(models.Model):
    _inherit = 'mail.activity'
    _rec_name = 'display_name'

    display_name = fields.Char(string="Display Name", compute='_compute_display_name', store=True)

    @api.depends('res_name')
    def _compute_display_name(self):
        """
        Odoo 17: Reemplaza name_get() con _compute_display_name()
        """
        for record in self:
            record.display_name = record.res_name or 'Activity'


    def open_window_for_model_of_activity(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'view_mode': 'form',
            'res_id': self.res_id,
        }
    
    def action_close(self):
        return {
             'type': 'ir.actions.client',
             'tag': 'reload',
             'params': {'wait': True}
         }
