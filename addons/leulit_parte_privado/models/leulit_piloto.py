# -*- encoding: utf-8 -*-
from odoo import models, fields


class LeulitPiloto(models.Model):
    _inherit = "leulit.piloto"

    privado = fields.Boolean(string="Piloto privado", help="Sus partes en papel se transcriben desde Vuelos > Parte piloto privado")
