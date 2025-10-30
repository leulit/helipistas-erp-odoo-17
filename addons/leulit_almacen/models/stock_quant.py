# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
import pyqrcode

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _name = 'stock.quant'
    _inherit = 'stock.quant'


    @api.depends('precio','quantity')
    def _total_qty(self):
        for item in self:
            item.precio_x_qty = item.precio * item.quantity


    def _search_total_qty(self, operator, value):
        ids = []
        for item in self.search([]):
            product_qty = item.precio * item.quantity
            if operator == '=':
                if product_qty == value:
                    ids.append(item.id)
            if operator == '<=':
                if product_qty <= value:
                    ids.append(item.id)
            if operator == '<':
                if product_qty < value:
                    ids.append(item.id)
            if operator == '>=':
                if product_qty >= value:
                    ids.append(item.id)
            if operator == '>':
                if product_qty > value:
                    ids.append(item.id)
            if operator == '!=':
                if product_qty != value:
                    ids.append(item.id)
        if ids:
            return  [('id','in',ids)]
        return  [('id','=','0')]
    

    precio = fields.Float(related='lot_id.precio', string='Precio unitario')
    proveedores_id_ant = fields.Char(related='lot_id.proveedores_id_ant', string='Proveedores')
    date_first_move = fields.Date(related='lot_id.date_first_move', string="Fecha primer movimiento")
    precio_x_qty = fields.Float(compute='_total_qty', search='_search_total_qty', string='Precio total')