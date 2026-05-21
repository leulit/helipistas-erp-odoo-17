# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    is_lost = fields.Boolean(
        string="Es etapa de pérdida",
        help="Si está marcado, mover un lead a esta etapa exige rellenar el motivo "
             "de pérdida mediante el botón «Perdido».",
    )
