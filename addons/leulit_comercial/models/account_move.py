# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    @api.model
    def create(self, vals):
        result = super(AccountMove, self).create(vals)
        sale = self.env['sale.order'].search([('invoice_ids','in',[result.id])])
        result.origin = sale.origin
        return result

    origin = fields.Char(string="Información")


    def save_from_app(self):
        _logger.error(self)
        datos = self._context.get('args',[])
        _logger.error(datos)
        self.search([('id','=',datos['factura_id'])]).write({'partner_id':datos['partner_id'],'state':datos['state'],'ref':datos['ref'],'invoice_date':datos['invoice_date']})
        return True