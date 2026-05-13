# -*- encoding: utf-8 -*-
from odoo import fields, models


class MgmtsystemHazard(models.Model):
    _inherit = "mgmtsystem.hazard"
    _description = "Análisis de Riesgos"

    risk_type_id = fields.Many2one(string="Peligro")
    action_ids = fields.Many2many(
        "mgmtsystem.action",
        "leulit_hazard_action_rel",
        "hazard_id",
        "action_id",
        string="Acciones",
    )
