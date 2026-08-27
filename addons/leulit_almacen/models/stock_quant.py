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
    

    def _sync_estanteria(self):
        # Meter una pieza en una caja (o sacarla) le cambia el sitio. Se propaga desde el quant y
        # no desde los sitios que escriben package_id para cubrir tambien los caminos del core,
        # como el boton nativo "Poner en paquete".
        self.mapped('lot_id')._sync_estanteria_caja()


    @api.model_create_multi
    def create(self, vals_list):
        # Un quant puede nacer ya dentro de una caja (recepcion sobre un paquete, validar un
        # albaran con "Poner en paquete"): sin esto la pieza se queda diciendo donde estaba antes.
        quants = super(StockQuant, self).create(vals_list)
        quants.filtered('package_id')._sync_estanteria()
        return quants


    def write(self, vals):
        res = super(StockQuant, self).write(vals)
        if 'package_id' in vals:
            self._sync_estanteria()
        return res


    def unlink(self):
        # Se queda sin existencias en la caja: deja de estar donde estaba la caja.
        lotes = self.filtered('package_id').mapped('lot_id')
        res = super(StockQuant, self).unlink()
        lotes._sync_estanteria_caja()
        return res


    estanteria_id = fields.Many2one(related='package_id.estanteria_id', comodel_name='stock.location', string='Estantería')
    precio = fields.Float(related='lot_id.precio', string='Precio unitario')
    proveedores_id_ant = fields.Char(related='lot_id.proveedores_id_ant', string='Proveedores')
    date_first_move = fields.Date(related='lot_id.date_first_move', string="Fecha primer movimiento")
    precio_x_qty = fields.Float(compute='_total_qty', search='_search_total_qty', string='Precio total')