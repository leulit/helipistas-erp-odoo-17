# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta, time
import logging
_logger = logging.getLogger(__name__)


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.depends('employee_id')
    def _get_piloto(self):
        for item in self:
            item.piloto_id = self.env['leulit.piloto'].search([('employee', '=', item.employee_id.id)], limit=1)

    @api.depends('product_id')
    def _compute_is_dieta_pernocta(self):
        for item in self:
            item.is_dieta_pernocta = False
            if item.piloto_id:
                item.is_dieta_pernocta = item.product_id.name in ['Dieta con pernocta', 'Dieta sin pernocta', 'Plus de disponibilidad/activación']

    @api.onchange('product_id', 'date')
    def _onchange_product_id_date(self):
        if self.is_dieta_pernocta:
            if self.product_id.name == 'Dieta con pernocta':
                if self.piloto_id:
                    if 5 <= self.date.month <= 9:
                        self.sudo().price_unit = self.piloto_id.dieta_ta
                    else:
                        self.sudo().price_unit = self.piloto_id.dieta_tb
            if self.product_id.name == 'Plus de disponibilidad/activación':
                if self.piloto_id:
                    self.sudo().price_unit = self.piloto_id.plus_activacion


    piloto_id = fields.Many2one(compute=_get_piloto, comodel_name="leulit.piloto", string="Piloto")
    is_dieta_pernocta = fields.Boolean(compute=_compute_is_dieta_pernocta, string="Dieta con pernocta")