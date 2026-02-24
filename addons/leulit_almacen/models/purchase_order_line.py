import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from datetime import datetime, date, timedelta, time
_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'

    @api.depends('product_id','product_qty')
    def _get_cantidades(self):
        self.env.companies = self.env['res.company'].search([('name','in',['Icarus Manteniment S.L.','Helipistas S.L.'])])
        for item in self:
            quant_ids = self.env['stock.quant'].search([('product_id','=',item.product_id.id),('on_hand', '=', True)])
            cantidad_stock = 0
            for quant in quant_ids:
                cantidad_stock += quant.quantity
            item.en_stock = cantidad_stock
            
            albaranes = self.env['stock.picking'].search([('state','in',['assigned'])])
            cantidad_prevision = 0
            for linea in albaranes.move_ids_without_package:
                if linea.product_id.id == item.product_id.id:
                    cantidad_prevision += linea.product_uom_qty
            item.en_prevision = cantidad_prevision
            
            pedidos = self.env['purchase.order'].search([('state','in',['draft','sent'])])
            cantidad_borrador = 0
            for linea in pedidos.order_line:
                if linea.product_id.id == item.product_id.id:
                    cantidad_borrador += linea.product_qty
            item.en_borrador = cantidad_borrador


    @api.constrains('product_id','order_id')
    def _check_duplicate_product(self):
        for line in self:
            domain = [('order_id', '=', line.order_id.id), ('product_id', '=', line.product_id.id), ('display_type','=',False)]
            other_lines = self.search(domain)
            if len(other_lines) > 1:
                raise ValidationError(_("No puede tener líneas de presupuesto duplicadas con el mismo producto en una orden de compra."))


    en_stock = fields.Float(compute=_get_cantidades, string="En stock", help="Suma de cantidades en stock.")
    en_prevision = fields.Float(compute=_get_cantidades, string="En previsión", help="Suma de cantidades en albaranes de entrada en estado 'Preparado'.")
    en_borrador = fields.Float(compute=_get_cantidades, string="En borrador", help="Suma de cantidades en presupuestos de compra con estado en 'Petición presupuesto' o en 'Solicitud de presupuesto enviada'")


    def write(self, vals):
        for line in self:
            if line.order_id.is_locked and not self.env.user.has_group('leulit_almacen.RResponsable_almacen'):
                raise UserError("No se pueden modificar líneas mientras el pedido está bloqueado.")
        return super().write(vals)

    @api.model
    def create(self, vals):
        order = self.env['purchase.order'].browse(vals.get('order_id'))
        if order.is_locked and not self.env.user.has_group('leulit_almacen.RResponsable_almacen'):
            raise UserError("No se pueden añadir líneas mientras el pedido está bloqueado.")
        return super().create(vals)

