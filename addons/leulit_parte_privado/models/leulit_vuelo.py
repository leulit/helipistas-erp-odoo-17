# -*- encoding: utf-8 -*-
from odoo import models, fields, api


class LeulitVuelo(models.Model):
    _inherit = "leulit.vuelo"

    privado_introducido_por = fields.Many2one(comodel_name="res.users", string="Introducido por (parte privado)", readonly=True)

    @api.constrains('airtime')
    def _check_airtime_multiple_of_6_minutes(self):
        # Parte privado: airtime = tiempo de servicio - 6 min exactos, no en décimas de hora.
        # La constraint original sigue aplicando al resto de vuelos.
        return super(LeulitVuelo, self.filtered(lambda v: not v.privado_introducido_por))._check_airtime_multiple_of_6_minutes()
