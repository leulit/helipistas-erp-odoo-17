# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    medium_id = fields.Many2one(required=True)
