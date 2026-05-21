# -*- encoding: utf-8 -*-
from odoo import fields, models


class MgmtsystemAction(models.Model):
    _inherit = "mgmtsystem.action"

    risk_type_id = fields.Many2one("mgmtsystem.hazard.risk.type", string="Peligro")
