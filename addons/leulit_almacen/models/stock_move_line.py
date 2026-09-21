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

    def action_done_stock_move(self):
        for move_line in self:
            if move_line.move_id:
                move_line.move_id._action_done()
        return True
    
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


    def _prepare_new_lot_vals(self):
        self.ensure_one()
        return {
            'name': self.lot_name,
            'product_id': self.product_id.id,
            'company_id': self.company_id.id,
            'revision': self.revision,
            'fecha_caducidad': self.fecha_caducidad
        }

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
    estanteria_destino_id = fields.Many2one(
        comodel_name="stock.location", string="Estantería", ondelete='restrict',
        domain=lambda self: self.env['stock.quant.package']._domain_estanteria(),
        help="Estantería donde se coloca la pieza al validar. La caja destino se elige entre las "
             "cajas de esta estantería. Si no hay caja, la pieza queda suelta en la estantería.")


    def _get_lote_existente(self):
        self.ensure_one()
        if not (self.lot_name and self.product_id):
            return self.env['stock.lot']
        return self.env['stock.lot'].search([
            ('name', '=', self.lot_name),
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
        ], limit=1)


    @api.onchange('lot_name')
    def _onchange_lot_name_ubicacion(self):
        # Si el S/N/lote ya existe, se propone su sitio actual: a la vista queda a que caja y
        # estanteria va y evita recepcionar un duplicado sin darse cuenta.
        lot = self._get_lote_existente()
        if lot:
            self.estanteria_destino_id = lot.estanteria_id
            self.result_package_id = lot.caja_id


    @api.onchange('estanteria_destino_id')
    def _onchange_estanteria_destino_id(self):
        # La caja tiene que estar en la estanteria elegida: si ya no lo esta, se vacia.
        if self.result_package_id and self.result_package_id.estanteria_id != self.estanteria_destino_id:
            self.result_package_id = False
        return self._aviso_reubicacion()


    @api.onchange('result_package_id')
    def _onchange_result_package_id_ubicacion(self):
        return self._aviso_reubicacion()


    def _aviso_reubicacion(self):
        """Un lote va siempre en una sola caja: si la pieza ya existe en otro sitio se avisa, sin
        bloquear (puede ser una reubicacion legitima)."""
        lot = self._get_lote_existente()
        if lot and (lot.caja_id or lot.estanteria_id) and (
                lot.caja_id != self.result_package_id or lot.estanteria_id != self.estanteria_destino_id):
            return {'warning': {
                'title': _('La pieza ya existe en almacén'),
                'message': _('"%s" ya está en la caja "%s", estantería "%s". Si continúas, se '
                             'reubicará.') % (lot.name, lot.caja_id.name or _('ninguna'),
                                              lot.estanteria_id.display_name or _('ninguna'))}}


    @api.constrains('estanteria_destino_id', 'result_package_id')
    def _check_caja_en_estanteria(self):
        for line in self:
            if line.result_package_id and line.estanteria_destino_id and \
                    line.result_package_id.estanteria_id != line.estanteria_destino_id:
                raise ValidationError(_(
                    'La caja "%s" no está en la estantería "%s".') % (
                        line.result_package_id.name, line.estanteria_destino_id.display_name))


    def _action_done(self):
        res = super(StockMoveLine, self)._action_done()
        # Con caja, la estanteria la propagan los hooks de stock.quant. Sin caja (pieza suelta)
        # se escribe en el lote; si el lote ya esta en una caja mandaria la caja, se deja.
        for line in self.exists().filtered(lambda l: l.estanteria_destino_id and l.lot_id and not l.result_package_id):
            if not line.lot_id.caja_id and line.lot_id.estanteria_id != line.estanteria_destino_id:
                line.lot_id.sudo().estanteria_id = line.estanteria_destino_id
        return res


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
