# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class account_move(models.Model):
    _inherit = 'account.move'

    @api.constrains("invoice_date")
    def _check_invoice_date_from_others(self):
        for account in self:
            if account.move_type == 'out_invoice':
                facturas_posteriores = self.search([('invoice_date','>',account.invoice_date),('id','!=',account.id),('move_type','=','out_invoice')])
                if len(facturas_posteriores) > 0:
                    break
                    # raise ValidationError(_("Hay factura con fecha de factura posterior a la fecha de la factura actual."))
    
    expense_sheet_id = fields.Many2one(comodel_name="hr.expense.sheet", string="Hoja de gastos")