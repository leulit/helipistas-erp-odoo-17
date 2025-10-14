# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, date, timedelta


class StockMoveScrap(models.TransientModel):
    _name = 'stock.move_scrap'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _description = 'Movimiento a Scrap'

    def _get_default_dest_location_id(self):
        return self.env['stock.location'].search([('name','=','Scrap'),('company_id','=',2)], limit=1).id

    def _get_default_location_id(self):
        return self.env['stock.location'].search([('name','=','Material Pendiente Decisión')], limit=1).id


    name = fields.Char(
        'Reference',  default=lambda self: _('Nuevo'),
        copy=False, readonly=True, required=True,
        )
    company_id = fields.Many2one('res.company', string='Compañia', default=2, required=True)
    origin = fields.Char(string='Información')
    product_id = fields.Many2one(
        'product.product', 'Producto', domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True, check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    tracking = fields.Selection(string='Product Tracking', readonly=True, related="product_id.tracking")
    lot_id = fields.Many2one(
        'stock.lot', 'Pieza', required=True,
         check_company=True, domain=[('product_qty','!=',0)])
    owner_id = fields.Many2one('res.partner', 'Propietario', default=1, check_company=True)
    move_id = fields.Many2one('stock.move', 'Scrap Move', readonly=True, check_company=True, copy=False)
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Ubicación Origen', required=True,
        domain="[('name', 'in', ['Material Pendiente Decisión','Material Nuevo','Material Útil'])]",
        default=_get_default_location_id, check_company=True)
    dest_location_id = fields.Many2one(
        'stock.location', 'Ubicación Destino', default=_get_default_dest_location_id,
        required=True, check_company=True)
    qty = fields.Float('Cantidad', default=1.0, required=True, digits='Product Unit of Measure')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')],
        string='Status', default="draft", readonly=True, tracking=True)
    date_done = fields.Datetime('Fecha', default=fields.Date.context_today)
    rotable_lifelimit = fields.Boolean(related="lot_id.rotable_lifelimit",string="Rotable / Life Limit")
    qty_available = fields.Float(related="lot_id.product_qty",string="Cantidad en Stock")
    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order", domain=[('done','=',False)])
    equipment = fields.Many2one(related="maintenance_request_id.equipment_id", comodel_name="maintenance.equipment", string="Equipo Work Order")

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            self.location_id = (self.picking_id.state == 'done') and self.picking_id.location_dest_id.id or self.picking_id.location_id.id

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if self.lot_id:
            self.product_id = self.lot_id.product_id.id
            self.qty = 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.tracking == 'serial':
                self.qty = 1
            self.product_uom_id = self.product_id.uom_id.id
            # Check if we can get a more precise location instead of
            # the default location (a location corresponding to where the
            # reserved product is stored)
            if self.picking_id:
                for move_line in self.picking_id.move_line_ids:
                    if move_line.product_id == self.product_id:
                        self.location_id = move_line.location_id if move_line.state != 'done' else move_line.location_dest_id
                        break

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            # Change the locations only if their company doesn't match the company set, otherwise
            # user defaults are overridden.
            if self.location_id.company_id != self.company_id:
                self.location_id = self.env['stock.location'].search([('name','=','Material Útil')], limit=1).id
            if self.dest_location_id.company_id != self.company_id:
                self.dest_location_id = self.env['stock.location'].search([('name','=','Material Pendiente Decisión')], limit=1).id
        else:
            self.location_id = False
            self.dest_location_id = False

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('No se puede eliminar un movimiento ya creado'))
        return super(StockMoveScrap, self).unlink()

    def _prepare_move_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'origin': self.origin or self.picking_id.name or self.name,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'state': 'draft',
            'product_uom_qty': self.qty,
            'location_id': self.location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'date': self.date_done,
            'move_line_ids': [(0, 0, {'product_id': self.product_id.id,
                                           'product_uom_id': self.product_uom_id.id, 
                                           'quantity': self.qty,
                                           'location_id': self.location_id.id,
                                           'date': self.date_done,
                                           'location_dest_id': self.dest_location_id.id,
                                           'owner_id': self.owner_id.id,
                                           'lot_id': self.lot_id.id, })],
            'picking_id': self.picking_id.id
        }

    def do_move_certificate(self):
        self._check_company()
        for move_certificate in self:
            move_certificate.name = self.with_context(force_company=2).env['ir.sequence'].next_by_code('stock.scrap') or _('New')
            move = self.env['stock.move'].create(move_certificate._prepare_move_values())
            move._action_done()
            move_certificate.write({'move_id': move.id, 'state': 'done'})
            move_certificate.date_done = fields.Datetime.now()
        return True

    def action_get_stock_picking(self):
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        action['domain'] = [('id', '=', self.picking_id.id)]
        return action

    def action_get_stock_move_lines(self):
        action = self.env['ir.actions.act_window']._for_xml_id('stock.stock_move_line_action')
        action['domain'] = [('move_id', '=', self.move_id.id)]
        return action

    def action_validate(self):
        self.ensure_one()
        if self.qty <= 0:
            raise UserError(_('Ingrese una cantidad positiva para el movimiento.'))
        fecha = self.date_done
        if self.product_id.type != 'product':
            return self.do_move_certificate()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        
        available_qty = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, strict=False)
        qty = self.product_uom_id._compute_quantity(self.qty, self.product_id.uom_id)
        if float_compare(available_qty, qty, precision_digits=precision) >= 0:
            self.do_move_certificate()
            move_line = self.env['stock.move.line'].search([('move_id','=',self.move_id.id)])
            if self.maintenance_request_id:
                move_line.maintenance_request_id = self.maintenance_request_id.id
            if self.rotable_lifelimit:
                move_line.is_rotable = True
            move_line.date = fecha
            self.move_id.date = fecha
            self.date_done = fecha

            return True 
        else:
            raise UserError('No tienes la cantidad suficiente en stock.')

    def action_validate_app(self):
        datos = self._context.get('args',[])
        pieza = self.env['stock.lot'].search([('id','=',datos['pieza'])])
        ubicacion = self.env['stock.location'].search([('id','=',datos['ubicacion'])])
        work_order = self.env['maintenance.request'].search([('id','=',datos['work_order'])])
        values = {
            'date_done' : datos['fecha'],
            'lot_id' : pieza.id,
            'product_id' : pieza.product_id.id,
            'product_uom_id' : pieza.product_id.uom_id.id,
            'qty' : datos['cantidad'],
            'location_id' : ubicacion.id,
            'maintenance_request_id' : work_order.id,
        }
        self = self.create(values)
        self.action_validate()


