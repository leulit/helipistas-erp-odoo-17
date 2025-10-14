# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, date, timedelta


class StockUninstall(models.TransientModel):
    _name = 'stock.uninstall'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _description = 'Uninstall'

    def _get_default_location_id(self):
        return self.env['stock.location'].search([('name','=','Equipamiento')], limit=1).id

    def _get_default_uninstall_location_id(self):
        return self.env['stock.location'].search([('name','=','Material Pendiente Decisión')], limit=1).id


    name = fields.Char(
        'Reference',  default=lambda self: _('Nuevo'),
        copy=False, readonly=True, required=True,
        )
    company_id = fields.Many2one('res.company', string='Compañia', default=2, required=True)
    origin = fields.Char(string='Información')
    product_id = fields.Many2one(
        'product.product', 'Producto', domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=False, check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        required=False, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    tracking = fields.Selection(string='Product Tracking', readonly=True, related="product_id.tracking")
    lot_id = fields.Many2one(
        'stock.lot', 'Pieza', required=False,
         check_company=True)
    owner_id = fields.Many2one('res.partner', 'Propietario', default=1, check_company=True)
    move_id = fields.Many2one('stock.move', 'Scrap Move', readonly=True, check_company=True, copy=False)
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Ubicación Origen', domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]",
        required=True, default=_get_default_location_id, check_company=True)
    uninstall_location_id = fields.Many2one(
        'stock.location', 'Ubicación Destino', default=_get_default_uninstall_location_id,
        domain="[('name', 'in', ['Material Pendiente Decisión','Scrap']), ('company_id', 'in', [company_id, False])]", required=True, check_company=True)
    uninstall_qty = fields.Float('Cantidad', default=1.0, required=True, digits='Product Unit of Measure')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')],
        string='Status', default="draft", readonly=True, tracking=True)
    date_done = fields.Datetime('Fecha', default=fields.Date.context_today)
    rotable_lifelimit = fields.Boolean(related="lot_id.rotable_lifelimit",string="Rotable / Life Limit")
    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order", domain=[('done','=',False)])
    equipment = fields.Many2one(related="maintenance_request_id.equipment_id", comodel_name="maintenance.equipment", string="Equipo Work Order")

    @api.model
    def create(self, vals):
        if 'lot_id' not in vals:
            raise UserError(_('Debe seleccionar una pieza para desinstalar.'))
        if 'product_uom_id' not in vals:
            raise UserError(_('Debe seleccionar una unidad de medida.'))
        if 'maintenance_request_id' not in vals:
            raise UserError(_('Debe seleccionar una orden de trabajo.'))
        return super(StockUninstall, self).create(vals)

    def action_create_lot(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Pieza',
            'res_model': 'stock.lot',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'default_company_id': self.company_id.id},
        }

    def print_etiqueta_pieza(self):
        return self.lot_id.print_etiqueta_pieza()

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            self.location_id = (self.picking_id.state == 'done') and self.picking_id.location_dest_id.id or self.picking_id.location_id.id

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if self.lot_id:
            self.product_id = self.lot_id.product_id.id
            self.uninstall_qty = 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.tracking == 'serial':
                self.uninstall_qty = 1
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
                self.location_id = self.env['stock.location'].search([('name','=','Equipamiento')], limit=1).id
            if self.uninstall_location_id.company_id != self.company_id:
                self.uninstall_location_id = self.env['stock.location'].search([('name','=','Material Pendiente Decisión')], limit=1).id
        else:
            self.location_id = False
            self.uninstall_location_id = False

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('No se puede eliminar un movimiento ya creado'))
        return super(StockUninstall, self).unlink()

    def _prepare_move_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'origin': self.origin or self.picking_id.name or self.name,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'state': 'draft',
            'product_uom_qty': self.uninstall_qty,
            'location_id': self.location_id.id,
            'location_dest_id': self.uninstall_location_id.id,
            'date': self.date_done,
            'move_line_ids': [(0, 0, {'product_id': self.product_id.id,
                                           'product_uom_id': self.product_uom_id.id, 
                                           'quantity': self.uninstall_qty,
                                           'location_id': self.location_id.id,
                                           'date': self.date_done,
                                           'location_dest_id': self.uninstall_location_id.id,
                                           'owner_id': self.owner_id.id,
                                           'lot_id': self.lot_id.id, })],
            'picking_id': self.picking_id.id
        }

    def do_uninstall(self):
        self._check_company()
        for uninstall in self:
            uninstall.name = self.with_context(force_company=2).env['ir.sequence'].next_by_code('stock.uninstall') or _('New')
            move = self.env['stock.move'].create(uninstall._prepare_move_values())
            move._action_done()
            uninstall.write({'move_id': move.id, 'state': 'done'})
            uninstall.date_done = fields.Datetime.now()
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
        if self.rotable_lifelimit:
            raise UserError(_('Es una pieza marcada como rotable, por favor cuando instales la nueva pieza rotable desde el menú Movimiento Instalación, te pedirá la pieza a desinstalar.'))
        if not self.lot_id or not self.product_id:
            raise UserError(_('Debe seleccionar una pieza para desinstalar.'))
        if not self.product_uom_id:
            raise UserError(_('Debe seleccionar una unidad de medida.'))
        if not self.maintenance_request_id:
            raise UserError(_('Debe seleccionar una orden de trabajo.'))
        if self.uninstall_qty <= 0:
            raise UserError(_('Ingrese una cantidad positiva para desinstalar.'))
        fecha = self.date_done
        if self.product_id.type != 'product':
            return self.do_uninstall()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        
        self.do_uninstall()
        move_line = self.env['stock.move.line'].search([('move_id','=',self.move_id.id)])
        if self.maintenance_request_id:
            move_line.maintenance_request_id = self.maintenance_request_id.id
        move_line.date = fecha
        self.move_id.date = fecha
        self.date_done = fecha

        return True 

    def action_validate_app(self):
        try:
            datos = self._context.get('args',[])
            pieza = self.env['stock.lot'].search([('id','=',datos['pieza'])])
            ubicacion = self.env['stock.location'].search([('id','=',datos['ubicacion'])])
            work_order = self.env['maintenance.request'].search([('id','=',datos['work_order'])])
            values = {
                'date_done' : datos['fecha'],
                'lot_id' : pieza.id,
                'product_id' : pieza.product_id.id,
                'product_uom_id' : pieza.product_id.uom_id.id,
                'uninstall_qty' : datos['cantidad'],
                'uninstall_location_id' : ubicacion.id,
                'maintenance_request_id' : work_order.id,
            }
            self = self.create(values)
            self.action_validate()
        except Exception as e:
            raise UserError(f"Error al validar la instalación: {str(e)}")

