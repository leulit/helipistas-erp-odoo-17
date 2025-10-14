# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime, date, timedelta


class StockInstall(models.TransientModel):
    _name = 'stock.install'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _description = 'Install'

    def _get_default_install_location_id(self):
        return self.env['stock.location'].search([('name','=','Equipamiento')], limit=1).id

    def _get_default_location_id(self):
        return self.env['stock.location'].search([('name','=','Material Nuevo')], limit=1).id

    def _get_default_uninstall_location_id(self):
        return self.env['stock.location'].search([('name','=','Material Pendiente Decisión')], limit=1).id


    name = fields.Char('Reference', default=lambda self: _('Nuevo'),copy=False, readonly=True, required=True)
    company_id = fields.Many2one('res.company', string='Compañia', default=2, required=True)
    origin = fields.Char(string='Información')
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade", check_company=True, domain="[('type', '!=', 'service')]", index=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    tracking = fields.Selection(string='Product Tracking', readonly=True, related="product_id.tracking")
    lot_id = fields.Many2one('stock.lot', 'Pieza', required=True, check_company=True, domain=[('product_qty','!=',0)])
    owner_id = fields.Many2one('res.partner', 'Propietario', default=1, check_company=True)
    move_id = fields.Many2one('stock.move', 'Scrap Move', readonly=True, check_company=True, copy=False)
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True)
    location_id = fields.Many2one('stock.location', 'Ubicación Origen', domain="[('name', 'in', ['Material Nuevo','Material Útil'])]", required=True, default=_get_default_location_id, check_company=True)
    install_location_id = fields.Many2one('stock.location', 'Ubicación Destino', default=_get_default_install_location_id, domain="[ ('company_id', 'in', [company_id, False])]", required=True, check_company=True)
    uninstall_location_id = fields.Many2one('stock.location', 'Ubicación Destino', default=_get_default_uninstall_location_id, domain="[('name', 'in', ['Material Pendiente Decisión','Scrap']), ('company_id', 'in', [company_id, False])]",  required=True, check_company=True)
    install_qty = fields.Float('Cantidad', default=1.0, required=True, digits='Product Unit of Measure')
    state = fields.Selection([('draft', 'Draft'),('done', 'Done')], string='Status', default="draft", readonly=True, tracking=True)
    date_done = fields.Datetime('Fecha', default=fields.Date.context_today)
    qty_available = fields.Float(related="lot_id.product_qty",string="Cantidad en Stock")
    rotable_lifelimit = fields.Boolean(related="lot_id.rotable_lifelimit",string="Rotable / Life Limit")
    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order", domain=[('done','=',False)])
    equipment = fields.Many2one(related="maintenance_request_id.equipment_id", comodel_name="maintenance.equipment", string="Equipo Work Order")
    desinstalacion_lot_id = fields.Many2one(comodel_name="stock.lot", string="Pieza a Desinstalar")


    def print_etiqueta_pieza(self):
        return self.desinstalacion_lot_id.print_etiqueta_pieza()

    @api.onchange('maintenance_request_id')
    def _onchange_maintenance_request(self):
        ids_lots = []
        if self.maintenance_request_id:
            for equipment in self.maintenance_request_id.equipment_id.get_all_childs():
                ids_lots.append(equipment.production_lot.id)
            return {
                'domain': {
                    'desinstalacion_lot_id': [('id', 'in', ids_lots)]
                }
            }
        else:
            return {
                'domain': {
                    'desinstalacion_lot_id': []
                }
            }

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            self.location_id = (self.picking_id.state == 'done') and self.picking_id.location_dest_id.id or self.picking_id.location_id.id

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if self.lot_id:
            self.product_id = self.lot_id.product_id.id
            self.install_qty = 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.tracking == 'serial':
                self.install_qty = 1
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
                self.location_id = self.env['stock.location'].search([('name','=','Material Nuevo')], limit=1).id
            if self.install_location_id.company_id != self.company_id:
                self.install_location_id = self.env['stock.location'].search([('name','=','Equipamiento')], limit=1).id
        else:
            self.location_id = False
            self.install_location_id = False

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('No se puede eliminar un movimiento ya creado'))
        return super(StockInstall, self).unlink()

    def _prepare_move_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'origin': self.origin or self.picking_id.name or self.name,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'state': 'draft',
            'product_uom_qty': self.install_qty,
            'location_id': self.location_id.id,
            'location_dest_id': self.install_location_id.id,
            'date': self.date_done,
            'move_line_ids': [(0, 0, {'product_id': self.product_id.id,
                                           'product_uom_id': self.product_uom_id.id, 
                                           'quantity': self.install_qty,
                                           'location_id': self.location_id.id,
                                           'date': self.date_done,
                                           'location_dest_id': self.install_location_id.id,
                                           'owner_id': self.owner_id.id,
                                           'lot_id': self.lot_id.id, })],
            'picking_id': self.picking_id.id
        }

    def do_install(self):
        self._check_company()
        for install in self:
            install.name = self.with_context(force_company=2).env['ir.sequence'].next_by_code('stock.install') or _('New')
            move = self.env['stock.move'].create(install._prepare_move_values())
            move._action_done()
            install.write({'move_id': move.id, 'state': 'done'})
            install.date_done = fields.Datetime.now()
        return True

    def _prepare_move_values_uninstall(self,name):
        self.ensure_one()
        return {
            'name': name,
            'origin': self.origin or self.picking_id.name or name,
            'company_id': self.company_id.id,
            'product_id': self.desinstalacion_lot_id.product_id.id,
            'product_uom': self.desinstalacion_lot_id.product_id.uom_id.id,
            'state': 'draft',
            'product_uom_qty': self.install_qty,
            'location_id': self.install_location_id.id,
            'location_dest_id': self.uninstall_location_id.id,
            'date': self.date_done,
            'move_line_ids': [(0, 0, {'product_id': self.desinstalacion_lot_id.product_id.id,
                                           'product_uom_id': self.desinstalacion_lot_id.product_id.uom_id.id, 
                                           'quantity': self.install_qty,
                                           'location_id': self.install_location_id.id,
                                           'date': self.date_done,
                                           'location_dest_id': self.uninstall_location_id.id,
                                           'owner_id': self.owner_id.id,
                                           'lot_id': self.desinstalacion_lot_id.id, })],
            'picking_id': self.picking_id.id
        }

    def do_uninstall(self):
        self._check_company()
        for uninstall in self:
            name = self.env['ir.sequence'].next_by_code('stock.uninstall') or _('New')
            move = self.env['stock.move'].create(uninstall._prepare_move_values_uninstall(name))
            move._action_done()
        return move

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
        if self.rotable_lifelimit and not self.desinstalacion_lot_id:
            raise UserError(_('Ingrese una pieza a desinstalar.'))
        if self.install_qty <= 0:
            raise UserError(_('Ingrese una cantidad positiva para instalar.'))
        fecha = self.date_done
        if self.product_id.type != 'product':
            return self.do_install()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        
        available_qty = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, strict=False)
        install_qty = self.product_uom_id._compute_quantity(self.install_qty, self.product_id.uom_id)
        if float_compare(available_qty, install_qty, precision_digits=precision) >= 0:
            self.do_install()
            move_line = self.env['stock.move.line'].search([('move_id','=',self.move_id.id)])
            if self.maintenance_request_id:
                move_line.maintenance_request_id = self.maintenance_request_id.id
            if self.rotable_lifelimit:
                move_line.is_rotable = True
            move_line.date = fecha
            self.move_id.date = fecha
            self.date_done = fecha

            if self.rotable_lifelimit:
                move = self.do_uninstall()
                move_line = self.env['stock.move.line'].search([('move_id','=',move.id)])
                if self.maintenance_request_id:
                    move_line.maintenance_request_id = self.maintenance_request_id.id
                move_line.is_rotable = True
                move_line_install = self.env['stock.move.line'].search([('move_id','=',self.move_id.id)])
                move_line_install.move_line_component_contrary_id = move_line
                move_line.move_line_component_contrary_id = move_line_install
                move_line.date = fecha
                move.date = fecha

                for equipment in self.maintenance_request_id.equipment_id.get_all_childs():
                    if equipment.production_lot.id == self.desinstalacion_lot_id.id:
                        equipment.effective_date = fecha
                        equipment.production_lot = self.lot_id
                        for subequipment in equipment.get_childs():
                            subequipment.aviso = 'Se ha instalado una nueva pieza en el equipo padre a fecha de ' + str(fecha.date()) + ' con el S/N ' + self.lot_id.name

            return True 
        else:
            raise UserError('No tienes la cantidad suficiente en stock.')

    def action_validate_app(self):
        try:
            datos = self._context.get('args',[])
            pieza_instalar = self.env['stock.lot'].search([('id','=',datos['pieza'])])
            pieza_desinstalar = self.env['stock.lot'].search([('id','=',datos['pieza_desinstalar'])]) if datos['pieza_desinstalar'] != 0 else False
            ubicacion = self.env['stock.location'].search([('id','=',datos['ubicacion'])])
            work_order = self.env['maintenance.request'].search([('id','=',datos['work_order'])])
            values = {
                'date_done' : datos['fecha'],
                'lot_id' : pieza_instalar.id,
                'product_id' : pieza_instalar.product_id.id,
                'product_uom_id' : pieza_instalar.product_id.uom_id.id,
                'desinstalacion_lot_id' : pieza_desinstalar.id if pieza_desinstalar else False,
                'install_qty' : datos['cantidad'],
                'location_id' : ubicacion.id,
                'maintenance_request_id' : work_order.id,
            }
            self = self.create(values)
            self.action_validate()
        except Exception as e:
            raise UserError(f"Error al validar la instalación: {str(e)}")



class StockWarnInsufficientQtyInstall(models.TransientModel):
    _name = 'stock.warn.insufficient.qty.install'
    _inherit = 'stock.warn.insufficient.qty'
    _description = 'Warn Insufficient Install Quantity'

    install_id = fields.Many2one('stock.install', 'Install')

    def _get_reference_document_company_id(self):
        return self.install_id.company_id

    def action_done(self):
        return self.install_id.do_install()

    def action_cancel(self):
        # FIXME in master: we should not have created the scrap in a first place
        if self.env.context.get('not_unlink_on_discard'):
            return True
        else:
            return self.install_id.sudo().unlink()