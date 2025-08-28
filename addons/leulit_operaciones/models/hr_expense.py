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

    @api.depends('product_id', 'company_id')
    def _compute_from_product_id_company_id(self):
        super(HrExpense, self)._compute_from_product_id_company_id()
        for expense in self.filtered('product_id'):
            if expense.product_id.name == 'Dieta con pernocta':
                if expense.piloto_id:
                    if 5 <= expense.date.month <= 9:
                        expense.sudo().unit_amount = expense.piloto_id.dieta_ta
                    else:
                        expense.sudo().unit_amount = expense.piloto_id.dieta_tb
            if expense.product_id.name == 'Plus de disponibilidad/activación':
                if expense.piloto_id:
                    expense.sudo().unit_amount = expense.piloto_id.plus_activacion


    piloto_id = fields.Many2one(compute=_get_piloto, comodel_name="leulit.piloto", string="Piloto")
    is_dieta_pernocta = fields.Boolean(compute=_compute_is_dieta_pernocta, string="Dieta con pernocta")