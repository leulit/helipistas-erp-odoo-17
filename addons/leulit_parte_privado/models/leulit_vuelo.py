# -*- encoding: utf-8 -*-
from odoo import models, fields


class LeulitVuelo(models.Model):
    _inherit = "leulit.vuelo"

    privado_introducido_por = fields.Many2one(comodel_name="res.users", string="Introducido por (parte privado)", readonly=True)
