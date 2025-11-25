# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    # @api.depends('expense_line_ids.total_amount','account_ids.amount_total')
    # def _compute_amount(self):
    #     for sheet in self:
    #         sheet.total_amount = sum(sheet.expense_line_ids.mapped('total_amount')) + sum(sheet.account_ids.mapped('amount_total'))

    # @api.depends('expense_line_ids.total_amount', 'expense_line_ids.tax_amount')
    # def _compute_amount(self):
    #     for sheet in self:
    #         sheet.total_amount = sum(sheet.expense_line_ids.mapped('total_amount'))
    #         sheet.total_tax_amount = sum(sheet.expense_line_ids.mapped('tax_amount'))
    #         sheet.untaxed_amount = sheet.total_amount - sheet.total_tax_amount

    def create_account_move(self):
        self.ensure_one()
        view = self.env.ref('account.view_move_form',raise_if_not_found=False)

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
            'view_id': view.id if view else False,
            'target': 'current',
            'context': context,
            'domain': domain,
        }

    @api.depends('account_move_ids', 'payment_state', 'approval_state')
    def _compute_state(self):
        """
        Evita que la hoja de gastos pase automáticamente a 'post' solo por tener facturas asociadas.
        Solo pasa a 'post' si está aprobada (approval_state == 'approve').
        """
        for sheet in self:
            if sheet.payment_state != 'not_paid':
                sheet.state = 'done'
            elif sheet.account_move_ids and sheet.approval_state == 'approve':
                sheet.state = 'post'
            elif sheet.approval_state:
                sheet.state = sheet.approval_state
            else:
                sheet.state = 'draft'