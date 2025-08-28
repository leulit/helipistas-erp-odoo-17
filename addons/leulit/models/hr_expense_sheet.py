# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"


    @api.depends('expense_line_ids.total_amount','account_ids.amount_total')
    def _compute_amount(self):
        for sheet in self:
            sheet.total_amount = sum(sheet.expense_line_ids.mapped('total_amount')) + sum(sheet.account_ids.mapped('amount_total'))

    def create_account_move(self):
        view_ref = self.env['ir.model.data'].get_object_reference('account','view_move_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_expense_sheet_id': self.id,
            'default_move_type': 'in_invoice',
            'default_invoice_origin': self.id,
            'default_origin': self.name,
        }
        domain=[('move_type', '=', 'in_invoice')]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factura',
            'res_model': 'account.move',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
            'domain': domain,
        }


    account_ids = fields.One2many(comodel_name="account.move", inverse_name="expense_sheet_id", string="Facturas")