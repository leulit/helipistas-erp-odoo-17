# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _name = 'stock.move.line'
    _inherit = 'stock.move.line'
 
    
    def write(self, vals):
        if 'date' in vals:
            for move_line in self:
                if move_line.picking_id:
                    vals['date'] = move_line.picking_id.scheduled_date
        res = super(StockMoveLine, self).write(vals)
        return res

    
    def open_stock_production_lot(self):
        view = self.env.ref('leulit_almacen.leulit_20221121_1017_form')
        return {
            'name': _('Pieza'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.lot',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': self.lot_id.id
        }


    @api.onchange('sn','lote','ref_origen','product_id')
    def _get_name_lot(self):
        context = dict(self.env.context)
        default_code = "N/A"
        if 'default_product_id' in context:
            product = self.env['product.product'].search([('id','=',context['default_product_id'])])
            default_code = product.default_code if product.default_code else 'N/A'
        if self.move_id.purchase_line_id:
            if self.move_id.purchase_line_id.order_id.partner_ref:
                self.ref_origen = self.move_id.purchase_line_id.order_id.partner_ref
        name_lot = '[{0}]-[{1}]-[{2}]-[{3}]'.format(default_code,self.sn,self.ref_origen,self.lote)
        self.lot_name = name_lot


    def _create_lot_ids_from_move_line_vals(self, vals_list, product_id, company_id):
        """Override: Crea lotes con revision y fecha_caducidad si están en vals_list."""
        lot_names = {vals['lot_name'] for vals in vals_list if vals.get('lot_name')}
        lot_ids = self.env['stock.lot'].search([
            ('product_id', '=', product_id),
            ('company_id', '=', company_id),
            ('name', 'in', list(lot_names)),
        ])

        lot_names_to_create = lot_names - set(lot_ids.mapped('name'))
        lots_to_create_vals = []
        for lot_name in lot_names_to_create:
            # Busca el primer vals con ese lot_name para extraer revision y fecha_caducidad
            vals_match = next((v for v in vals_list if v.get('lot_name') == lot_name), {})
            lot_val = {
                'product_id': product_id,
                'name': lot_name,
                'company_id': company_id,
            }
            if 'revision' in vals_match:
                lot_val['revision'] = vals_match['revision']
            if 'fecha_caducidad' in vals_match:
                lot_val['fecha_caducidad'] = vals_match['fecha_caducidad']
            lots_to_create_vals.append(lot_val)

        lot_ids |= self.env['stock.lot'].create(lots_to_create_vals)

        lot_id_by_name = {lot.name: lot.id for lot in lot_ids}
        for vals in vals_list:
            lot_name = vals.get('lot_name', None)
            if not lot_name:
                continue
            vals['lot_id'] = lot_id_by_name[lot_name]
            vals['lot_name'] = False


    id_movimiento = fields.Char('id movimiento antiguo')
    sn = fields.Char(string="Serial Number", default="N/A")
    lote = fields.Char(string="Lote", default="N/A")
    ref_origen = fields.Char(string="Referencia Origen", default="N/A")
    revision = fields.Char(string="Revisión", default="N/A")
    fecha_caducidad = fields.Date(string="Fecha Caducidad")
    equipment_id = fields.Many2one(comodel_name="maintenance.equipment", string="Helicoptero",domain=[('helicoptero','!=',False)])
    work_order = fields.Char(string="Work order")
    # repair_id = fields.Many2one(comodel_name="repair.order",string="Repair order")
    owner_id = fields.Many2one(
        'res.partner', 'From Owner',
        check_company=True,
        help="When validating the transfer, the products will be taken from this owner.",default=1)
    is_instalacion = fields.Boolean(compute="_get_tipo_instalacion", string="¿Es instalacion?", store=False, search="_search_is_instalacion")
    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order", domain=[('done','=',False)])
    equipment = fields.Many2one(related="maintenance_request_id.equipment_id", comodel_name="maintenance.equipment", string="Equipo Work Order")
    is_rotable = fields.Boolean(string="Movimiento de Componentes Rotables", default=False)
    move_line_component_contrary_id = fields.Many2one(comodel_name="stock.move.line", string="Movimiento de componente contrario")
    

    def _get_tipo_instalacion(self):
        location_destino = self.env['stock.location'].search([('name','in',['Equipamiento', 'Salida Almacén'])])
        for item in self:
            item.location_des = False
            if item.location_dest_id.id in location_destino.ids:
                item.is_instalacion = True

    
    def _search_is_instalacion(self, operator, value):
        location_destino = self.env['stock.location'].search([('name','in',['Equipamiento', 'Salida Almacén'])])
        ids = []
        for item in self.search([]):
            if item.location_dest_id.id in location_destino.ids:
                ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]
