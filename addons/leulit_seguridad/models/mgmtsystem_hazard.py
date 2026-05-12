# -*- encoding: utf-8 -*-
from odoo import fields, models


class MgmtsystemHazard(models.Model):
    _inherit = "mgmtsystem.hazard"

    risk_type_id = fields.Many2one(string="Peligro")
