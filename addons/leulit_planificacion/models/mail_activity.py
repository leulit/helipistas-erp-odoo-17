# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime


import logging
_logger = logging.getLogger(__name__)

class MailActivity(models.Model):
    _inherit = 'mail.activity'
    _rec_name = 'res_name'


    def name_get(self):
        res = []
        for record in self:
            name = record.res_name
            res.append((record.id, name))
        return res


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
