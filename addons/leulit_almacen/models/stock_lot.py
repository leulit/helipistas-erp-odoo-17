# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.tools import float_compare
import pyqrcode
import threading

_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _name = 'stock.lot'
    _inherit = 'stock.lot'

    def write(self, vals):
        result = super(StockLot, self).write(vals)
        if 'rel_docs' in vals:
            attachment = self.env['ir.attachment'].search([('rel_production_lot', '=', self.id)])
            if attachment:
                attachment.res_model = 'stock.lot'
                attachment.res_id = self.id
        return result

    @api.model
    def create(self, vals):
        if vals:
            if isinstance(vals, list):
                if len(vals) == 1:
                    vals = vals[0]
            if 'name' in vals:
                try:
                    name_list = vals['name'].split("]-[")
                    vals['sn'] = name_list[1].replace("[","").replace("]","")
                    vals['ref_origen'] = name_list[2].replace("[","").replace("]","")
                    vals['lote'] = name_list[3].replace("[","").replace("]","")
                except:
                    raise UserError("El nombre de la pieza deberia tener este formato '[PN]-[SN]-[Ref.origen]-[Lote]'")
        result = super(StockLot, self).create(vals)
        return result


    def copy(self, default=None):
        default = default or {}
        new_pieza = super(StockLot, self).copy(default)
        attachments_ids = self.env['ir.attachment'].search([('res_model','=','stock.lot'),('res_id','=',self.id)])
        for attach in attachments_ids:
            attach.copy(default={'res_id': new_pieza.id,'rel_production_lot':new_pieza.id})
        return new_pieza
    
    def add_datos_pieza(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_almacen', 'leulit_20221121_1017_form')
        view_id = view_ref and view_ref[1] or False

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Añadir + datos',
           'res_model'      : 'stock.lot',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'res_id'         : self.id,
            'flags'         : {'form': {'action_buttons': True}}
        }


    def print_etiqueta_pieza(self):
        if self.location_etiqueta != '':
            return self.print_etiqueta_report()
        else:
            if self.lot_hlp_ica:
                if self.lot_hlp_ica.location_etiqueta != '':
                    return self.lot_hlp_ica.print_etiqueta_report()
        return False


    def add_docs_stock_production_lot(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_almacen', 'leulit_20221215_1146_form')
        view_id = view_ref and view_ref[1] or False

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Añadir Documento',
           'res_model'      : 'stock.lot',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'res_id'         : self.id,
            'flags'         : {'form': {'action_buttons': True}}
        }


    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}


    def open_stock_production_lot(self):
        view_ref = self.env['ir.model.data'].get_object_reference('stock', 'view_production_lot_form')
        view_id = view_ref and view_ref[1] or False

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Pieza',
           'res_model'      : 'stock.lot',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'res_id'         : self.id,
        }


    def get_data_report(self):
        pn_alternativo = ''
        for producto_alternativo in self.product_id.optional_product_ids:
            pn_alternativo += '{0};'.format(producto_alternativo.default_code)
        formato = ''
        if self.location_etiqueta == 'MATERIAL NUEVO':
            formato = '2-1'
        if self.location_etiqueta == 'M. PTE. DECISIÓN':
            formato = '2-3'
        if self.location_etiqueta == 'MATERIAL ÚTIL':
            formato = '2-2'
        if self.location_etiqueta == 'MATERIAL INÚTIL':
            formato = '2-4'
        data = {
            'titulo': self.location_etiqueta,
            'pn': self.product_id.default_code if self.product_id.default_code else 'N/A',
            'pn_nombre' : self.product_id.name if self.product_id.name else 'N/A',
            'pn_alternativo' : pn_alternativo if pn_alternativo != '' else 'N/A',
            'sn' : self.sn if self.sn else 'N/A',
            'revision' : self.revision if self.revision else 'N/A',
            'lote' : self.lote if self.lote else 'N/A',
            'ref_origen' : self.ref_origen if self.ref_origen else 'N/A',
            'fecha_alta' : self.fecha_alta.strftime("%d-%m-%Y") if self.fecha_alta else 'N/A',
            'fecha_caducidad' : self.fecha_caducidad if self.fecha_caducidad else 'N/A',
            'codigo_wo' : self.last_maintenance_request_id.name if self.last_maintenance_request_id else 'N/A',
            'tsn' : self.tsn_actual if self.tsn_actual else 'N/A',
            'tso' : self.tso_actual if self.tso_actual else 'N/A',
            'o_life_hours' : self.o_life_hours if self.o_life_hours else 'N/A',
            'motivo_baja' : self.motivo_baja if self.motivo_baja else 'N/A',
            'formato' : formato,
            'qr' : self.qr,
            'posicion' : self.posicion if self.posicion else 'N/A',
            'sistema' : self.sistema if self.sistema else 'N/A',
        }
        return data

    def print_etiqueta_report(self):
        data = self.get_data_report()
        return self.env.ref('leulit_almacen.etiqueta_report').report_action(self, data=data)


    @api.depends('product_id')
    def _get_qr(self):
        for item in self:
            tiraqr = "%s | %s" %(item.last_move_stock_id.id,item.product_id.name)
            qr = pyqrcode.create(tiraqr,mode='binary')
            item.qr = qr.png_as_base64_str(3)

    def generate_qr(self):
        tiraqr = "%s | %s" %(self.last_move_stock_id.id,self.product_id.name)
        qr = pyqrcode.create(tiraqr,mode='binary')
        self.qr = qr.png_as_base64_str(3)


    @api.depends('moves')
    def _get_location_stock(self):
        for item in self:
            item.last_maintenance_request_id = False
            item.last_move_stock_id = False
            item.last_location_id = False
            item.location_etiqueta = ''
            if item.moves:
                moves = item.moves.filtered(lambda m: m.location_dest_id.name in ['Material Nuevo','Material Pendiente Decisión','Material Pendiente Decisión 2','Material Útil','Scrap']).sorted('date',reverse=True)
                if len(moves) > 0:
                    item.last_move_stock_id = moves[0].id
                    item.last_maintenance_request_id = moves[0].maintenance_request_id.id
                    if moves[0].location_dest_id.name == 'Material Nuevo':
                        location = 'MATERIAL NUEVO'
                        location_id = moves[0].location_dest_id.id
                    if moves[0].location_dest_id.name == 'Material Pendiente Decisión':
                        location = 'M. PTE. DECISIÓN'
                        location_id = moves[0].location_dest_id.id
                    if moves[0].location_dest_id.name == 'Material Pendiente Decisión 2':
                        location = 'M. PTE. DECISIÓN'
                        location_id = moves[0].location_dest_id.id
                    if moves[0].location_dest_id.name == 'Material Útil':
                        location = 'MATERIAL ÚTIL'
                        location_id = moves[0].location_dest_id.id
                    if moves[0].location_dest_id.name == 'Scrap':
                        location = 'MATERIAL INÚTIL'
                        location_id = False
                    item.location_etiqueta = location
                    item.last_location_id = location_id


    @api.depends('location_etiqueta','lot_hlp_ica')
    def _get_printable_etiqueta(self):
        for item in self:
            item.can_print = False
            if item.location_etiqueta != '' and item.location_etiqueta != False:
                item.can_print = True
            else:
                if item.lot_hlp_ica:
                    if item.lot_hlp_ica.location_etiqueta != '' and item.lot_hlp_ica.location_etiqueta != False:
                        item.can_print = True


    @api.depends('moves')
    def _get_first_move(self):
        for item in self:
            item.first_move = False
            item.date_first_move = False
            if item.moves:
                moves = item.moves.sorted('date')
                item.first_move = moves[0].id
                item.date_first_move = moves[0].date


    def _search_first_move_location(self, operator, value):
        ids = []
        for item in self.search([]):   
            if item.moves:
                moves = item.moves.sorted('date')
                name = moves[0].location_dest_id.name.upper()
                if operator == 'ilike':
                    if value.upper() in name:
                        ids.append(item.id)
                if operator == 'not ilike':
                    if value.upper() not in name:
                        ids.append(item.id)
        if ids:
            return  [('id','=',ids)]
        return  [('id','=','0')]


    def _search_first_move_date(self, operator, value):
        ids = []
        for item in self.search([]):   
            if item.moves:
                moves = item.moves.sorted('date')
                value_date = datetime.strptime(value,"%Y-%m-%d")
                date = moves[0].date
                if operator == '=':
                    if date == value_date:
                        ids.append(item.id)
                if operator == '<=':
                    if date <= value_date:
                        ids.append(item.id)
                if operator == '<':
                    if date < value_date:
                        ids.append(item.id)
                if operator == '>=':
                    if date >= value_date:
                        ids.append(item.id)
                if operator == '>':
                    if date > value_date:
                        ids.append(item.id)
                if operator == '!=':
                    if date != value_date:
                        ids.append(item.id)
        if ids:
            return  [('id','=',ids)]
        return  [('id','=','0')]



    @api.onchange('sn','lote','ref_origen','product_id')
    def _get_name_lot(self):
        for item in self:
            if not item.sn:
                item.sn = "N/A"
            if not item.lote:
                item.lote = "N/A"
            if not item.ref_origen:
                item.ref_origen = "N/A"

            if item.product_id:
                default_code = item.product_id.default_code
            else:
                default_code = 'N/A'
            name_lot = '[{0}]-[{1}]-[{2}]-[{3}]'.format(default_code,item.sn,item.ref_origen,item.lote)
            item.name = name_lot


    @api.depends('calibraciones.proxima_calibracion')
    def _get_proxima_calibracion(self):
        for item in self:
            item.fecha_proxima_calibracion = False
            if item.necesita_calibracion:
                for calibracion in item.calibraciones:
                    if calibracion.calibrado == True:
                        item.fecha_proxima_calibracion = calibracion.proxima_calibracion


    @api.depends('product_qty','motivo_baja','necesita_calibracion')
    def _set_estado_from_qty(self):
        for item in self:
            item.estado = False
            fuera_servicio = False
            if item.necesita_calibracion:
                flag = False
                calibraciones = self.env['leulit.calibracion'].search([('herramienta','=',item.id)])
                for calibracion in calibraciones:
                    if calibracion.calibrado == True:
                        flag = True
                if len(calibraciones) == 0:
                    flag = True
                if flag == False:
                    item.estado = 'fuera_servicio'
                    fuera_servicio = True
            if fuera_servicio == False:
                if item.product_qty > 0:
                    item.estado = 'operativo'
                else:
                    item.estado = 'revision'
            if item.motivo_baja:
                item.estado = 'fuera_servicio'


    @api.depends('calibraciones','necesita_calibracion')
    def _get_semaforo_calibraciones(self):
        for item in self:
            if item.necesita_calibracion:
                item.semaforo_calibracion = 'red'
                for calibracion in item.calibraciones:
                    if calibracion.calibrado == True:
                        if (calibracion.proxima_calibracion - datetime.now().date()).days < 30:
                            item.semaforo_calibracion = 'yellow'
                        else:
                            item.semaforo_calibracion = 'green'
            else:
                item.semaforo_calibracion = 'green'

                
    def _get_equipment(self):
        for item in self:
            item.equipment_id = self.env['maintenance.equipment'].search([('production_lot', '=', item.id)], limit=1)


    id_pieza = fields.Char(string='id pieza antiguo')
    qr = fields.Binary(compute=_get_qr, store=False, string='QR')
    moves = fields.One2many(comodel_name="stock.move.line", inverse_name="lot_id", string="Movimientos")
    last_move_stock_id = fields.Many2one(comodel_name="stock.move.line", compute=_get_location_stock, store=False, string="Última ubicación")
    location_etiqueta = fields.Char(compute=_get_location_stock, store=False, string="Última ubicación en stock")
    last_location_id = fields.Many2one(comodel_name="stock.location", compute=_get_location_stock, store=False, string="ID Última ubicación en stock")
    first_move = fields.Many2one(compute=_get_first_move, comodel_name="stock.move.line", store=False, string="Primer movimiento", search=_search_first_move_location)
    lote = fields.Char(string="Lote", default="N/A")
    ref_origen = fields.Char(string="Referencia Origen", default="N/A")
    revision = fields.Char(string="Revisión", default="N/A")
    fecha_alta = fields.Datetime(related="first_move.date", string="Fecha Alta")
    fecha_caducidad = fields.Date(string="Fecha Caducidad")
    o_life_hours = fields.Float(string="Vida Operativa")
    motivo_baja = fields.Selection(selection=[('deterioro', 'Deterioro'),('caducidad','Caducidad'),('agotamiento_potencial', 'Agotamiento potencial'), ('varios', 'Varios')], string="Motivo de la baja")
    last_maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", compute=_get_location_stock, string="Última Work Order")
    interval_hours = fields.Integer('Intevalo Horas')
    interval_days = fields.Integer('Intervalo Dias')
    tolerance_hours = fields.Integer('Tolerancia Horas')
    tolerance_days = fields.Integer('Tolerancia Dias')
    rel_stock_picking = fields.Many2one(comoddel_name="stock.picking",string="Albarán de entrada")
    rel_docs = fields.One2many(comodel_name='ir.attachment', inverse_name='rel_production_lot', string='Documentos')
    lot_hlp_ica = fields.Many2one(comodel_name='stock.lot', string='Pieza HLP-ICA')
    can_print = fields.Boolean(compute=_get_printable_etiqueta, store=False, string="¿Se puede imprimir etiqueta?")
    categoria_product = fields.Many2one(related="product_id.categ_id",comodel_name="product.category",string="Categoria Producto")
    medicion = fields.Char('Medición')
    necesita_calibracion = fields.Boolean('Necesita calibración')
    frecuencia_meses = fields.Integer('Frecuencia (meses)')
    fabricante = fields.Char('Fabricante')
    calibraciones = fields.One2many(comodel_name='leulit.calibracion', inverse_name='herramienta', string='Calibraciones')
    fecha_proxima_calibracion = fields.Date(compute=_get_proxima_calibracion, string="Próxima calibración")
    estado = fields.Selection(compute=_set_estado_from_qty, selection=[('operativo','Operativo'),('revision','En Revisión'),('fuera_servicio','Fuera de Servicio')], string="Estado")
    semaforo_calibracion = fields.Char(compute=_get_semaforo_calibraciones,string='Semáforo', store=False,
                                       help="""Si necesita calibración, verde: si tiene una calibración vigente, 
                                       amarillo: si quedan menos de 30 dias para la siguiente calibración, 
                                       rojo: si no tiene una calibración vigente. 
                                       Si no necesita calibración siempre se mostrará en verde."""
                                       )
    is_boroscopo = fields.Boolean(string="Boroscopo")
    
    precio = fields.Float(string='Precio unitario')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    product_qty = fields.Float('Lot Quantity', compute='_product_qty', search='_search_product_qty')
    precio_x_qty = fields.Float(compute='_total_qty', search='_search_total_qty', string='Precio total')
    qty_available = fields.Float(string='Product Quantity', related='product_id.qty_available')

    proveedores_id_ant = fields.Char(string='Proveedores')
    date_first_move = fields.Date(compute=_get_first_move, search=_search_first_move_date ,string="Fecha primer movimiento")

    update_stock = fields.Boolean(string="Actualizado")
    active = fields.Boolean(default=True)
    posicion = fields.Char(string="Posición")
    sistema = fields.Char(string="Sistema")
    rotable_lifelimit = fields.Boolean(related="product_id.rotable_lifelimit",string="Rotable/Life Limit")
    plan_id = fields.Many2one(comodel_name="maintenance.plan", string="Plan")
    equipment_id = fields.Many2one(compute=_get_equipment, comodel_name="maintenance.equipment", string="Componente")


    def create_form_one(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230706_1118_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'pieza': self.id,
            'default_fecha': datetime.now().date(),
            'default_certificador': self.env.user.partner_id.getMecanico()
        }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Form One',
            'res_model': 'leulit.maintenance_form_one',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }


    @api.depends('quant_ids', 'quant_ids.quantity')
    def _product_qty(self):
        for lot in self:
            # We only care for the quants in internal or transit locations.
            quants = lot.quant_ids.filtered(lambda q: q.location_id.usage == 'internal' or (q.location_id.usage == 'transit' and q.location_id.company_id))
            lot.product_qty = sum(quants.mapped('quantity'))


    def _search_product_qty(self, operator, value):
        ids = []
        for item in self.search([]):
            if item.quant_ids:
                quants = item.quant_ids.filtered(lambda q: q.location_id.usage == 'internal' or (q.location_id.usage == 'transit' and q.location_id.company_id))
                product_qty = sum(quants.mapped('quantity'))
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
            return  [('id','=',ids)]
        return  [('id','=','0')]
    

    @api.depends('precio','product_qty','currency_id')
    def _total_qty(self):
        for item in self:
            precio_unitario = item.precio
            if item.currency_id:
                if item.currency_id.id == 2:
                    precio_unitario = item.precio * 0.9
            item.precio_x_qty = precio_unitario * item.product_qty


    def _search_total_qty(self, operator, value):
        ids = []
        for item in self.search([]):
            product_qty = item.precio * item.product_qty
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
            return  [('id','=',ids)]
        return  [('id','=','0')]

    
    def set_update_prices(self):
        _logger.error("set_update_prices ")
        threaded_calculation = threading.Thread(target=self.run_update_prices, args=([]))
        _logger.error("set_update_prices start thread")
        threaded_calculation.start()
        return {}

    def run_update_prices(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            try:
                env = api.Environment(new_cr, self.env.uid, self.env.context)
                StockProductionLot = env['stock.lot']
                piezas = StockProductionLot.search([('create_date', '>=', '2025-01-01'),('precio', '=', 0)])
                for pieza in piezas:
                    precio = None
                    currency_id = None
                    # Buscar en las órdenes de compra relacionadas
                    for purchase in pieza.purchase_order_ids:
                        for line in purchase.order_line:
                            if line.product_id.id == pieza.product_id.id:
                                precio = line.price_unit
                                currency_id = purchase.currency_id.id
                                break
                        if precio is not None:
                            break
                    # Si no se encontró en purchase_order_ids, buscar en el primer movimiento
                    if precio is None and pieza.first_move and pieza.first_move.picking_id and pieza.first_move.picking_id.purchase_id:
                        for line in pieza.first_move.picking_id.purchase_id.order_line:
                            if line.product_id.id == pieza.product_id.id:
                                precio = line.price_unit
                                currency_id = line.order_id.currency_id.id
                                break
                    # Actualizar si se encontró precio
                    if precio is not None:
                        pieza.write({
                            'precio': precio,
                            'currency_id': currency_id,
                        })
                        _logger.info(f'Actualizado precio para pieza {pieza.name} ({pieza.id}): {precio} {currency_id}')
                    else:
                        _logger.warning(f'No se encontró precio para pieza {pieza.name} ({pieza.id})')
                new_cr.commit()
            except Exception as e:
                _logger.error(f'Error en run_update_prices: {e}')
                new_cr.rollback()
            finally:
                new_cr.close()
                _logger.error('###### FIN  ->  CRON UPDATE PRICES ######')


    def create_moves_app(self):
        datos = self._context.get('args',[])
        movimiento_anterior = self.env['stock.move.line'].sudo().search([('location_dest_id','=',datos['location_id']),('lot_id','=',datos['lote_id'])])
        move = self.env['stock.move'].sudo().create({'name':datos['name_move'],'product_id':datos['product_id'],'location_id':datos['location_id'],'location_dest_id':datos['location_dest_id'],'product_uom_qty':datos['quantity'],'company_id':datos['company_id'],'product_uom':datos['product_uom'],'origin':datos['origin'],'reference':datos['reference'],'date':datos['date']})
        move.reference = datos['reference']
        self.env['stock.move.line'].sudo().create({'work_order':datos['work_order'],'equipment_id':datos['equipment'],'owner_id':movimiento_anterior.owner_id.id,'move_id':move.id,'product_id':datos['product_id'],'date':datos['date'],'reference':datos['reference'],'location_id':datos['location_id'],'location_dest_id':datos['location_dest_id'],'quantity':datos['quantity'],'product_uom_qty':datos['quantity'],'lot_id':datos['lote_id'], 'company_id':datos['company_id'], 'product_uom_id':datos['product_uom']}) 
        move.state = 'done'
        producto = self.env['product.product'].search([('id','=',datos['product_id'])])
        if producto.type == 'product':
            self.env['stock.quant'].sudo().create({'product_id':datos['product_id'],'company_id':datos['company_id'],'location_id':datos['location_id'],'lot_id':datos['lote_id'],'quantity':-datos['quantity']})
            self.env['stock.quant'].sudo().create({'product_id':datos['product_id'],'company_id':datos['company_id'],'location_id':datos['location_dest_id'],'lot_id':datos['lote_id'],'quantity':datos['quantity']})
            

    def create_adjustment_move_app(self):
        datos = self._context.get('args',[])
        if datos['location_id'] != 18:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            location_id = self.env['stock.location'].sudo().search([('id','=',datos['location_id'])])
            product_id = self.env['product.product'].sudo().search([('id','=',datos['product_id'])])
            lot_id = self.env['stock.lot'].sudo().search([('id','=',datos['lote_id'])])
            available_qty = self.env['stock.quant']._get_available_quantity(product_id, location_id, lot_id, strict=False)
            install_qty = product_id.uom_id._compute_quantity(datos['quantity'], product_id.uom_id)
            if float_compare(available_qty, install_qty, precision_digits=precision) < 0:
                raise UserError(_('No hay suficiente cantidad en stock para ajustar.'))
        move = self.env['stock.move'].sudo().create({'name':datos['name_move'],'product_id':datos['product_id'],'location_id':datos['location_id'],'location_dest_id':datos['location_dest_id'],'product_uom_qty':datos['quantity'],'company_id':datos['company_id'],'product_uom':datos['product_uom'],'origin':datos['origin'],'reference':datos['reference'],'date':datos['date']})
        move.reference = datos['reference']
        self.env['stock.move.line'].sudo().create({'move_id':move.id,'product_id':datos['product_id'],'date':datos['date'],'reference':datos['reference'],'location_id':datos['location_id'],'location_dest_id':datos['location_dest_id'],'quantity':datos['quantity'],'product_uom_qty':datos['quantity'],'lot_id':datos['lote_id'], 'company_id':datos['company_id'], 'product_uom_id':datos['product_uom']}) 
        move.state = 'done'
        producto = self.env['product.product'].search([('id','=',datos['product_id'])])
        if producto.type == 'product':
            self.env['stock.quant'].sudo().create({'product_id':datos['product_id'],'company_id':datos['company_id'],'location_id':datos['location_id'],'lot_id':datos['lote_id'],'quantity':-datos['quantity']})
            self.env['stock.quant'].sudo().create({'product_id':datos['product_id'],'company_id':datos['company_id'],'location_id':datos['location_dest_id'],'lot_id':datos['lote_id'],'quantity':datos['quantity']})
