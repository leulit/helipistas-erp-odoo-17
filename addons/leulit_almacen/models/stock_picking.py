# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
import io
import re
import base64
from pypdf import PdfWriter, PdfReader
from odoo.addons.web.controllers.main import Binary

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'


    def write(self, vals):
        if 'date_done' in vals:
            for picking in self:
                if picking.scheduled_date:
                    vals['date_done'] = picking.scheduled_date
                else:
                    raise UserError('Falta rellenar el campo fecha prevista.')
        res = super(StockPicking, self).write(vals)
        return res

    def add_docs_stock_production_lot_all(self):
        attachments_ids = self.env['ir.attachment'].search([('res_model','=','stock.picking'),('res_id','=',self.id)])
        for lot in self.rel_stock_production_lot:
            for attach in attachments_ids:
                new_attach = attach.copy()
                new_attach.res_id = lot.id
                new_attach.res_model = 'stock.lot'
                new_attach.rel_production_lot = lot.id


    def _get_stock_production_lot_from_stock_move_line(self):
        for item in self:
            ids = []
            for line in self.env['stock.move.line'].search([('picking_id','=',item.id)]):
                if line.lot_id:
                    if not 'HLP' in line.lot_id.name:
                        ids.append(line.lot_id.id)
            item.rel_stock_production_lot = self.env['stock.lot'].search([('id','in',ids)])

    
    def create_moves_to_icarus(self):
        location_origen = self.env['stock.location'].search([('name','=','Stock'),('company_id','=',1)])
        location_destino = self.env['stock.location'].search([('name','=','Material Nuevo')])
        moves = self.env['stock.move'].search([('picking_id','=',self.id)])
        for move_hlp in moves:
            move = self.env['stock.move'].sudo().create({'name':move_hlp.name,'product_id':move_hlp.product_id.id,'location_id':location_origen.id,'location_dest_id':location_destino.id,'product_uom_qty':move_hlp.product_uom_qty,'company_id':2,'product_uom':move_hlp.product_uom.id,'origin':move_hlp.origin,'reference':move_hlp.reference,'date':move_hlp.date})
            move.reference = move_hlp.reference
            move_lines =  self.env['stock.move.line'].search([('move_id','=',move_hlp.id)])
            for move_line_hlp in move_lines:
                name_lot = move_line_hlp.lot_id.name
                move_line_hlp.lot_id.name = move_line_hlp.lot_id.name + "-[HLP]"
                pieza = move_line_hlp.lot_id.copy(default={'name': name_lot,'company_id':2})
                move_line_hlp.lot_id.lot_hlp_ica = pieza.id
                pieza.lot_hlp_ica = move_line_hlp.lot_id.id
                self.env['stock.move.line'].sudo().create({'picking_id':self.id,'owner_id':move_line_hlp.owner_id.id,'move_id':move.id,'product_id':move_line_hlp.product_id.id,'date':move_line_hlp.date,'reference':move_line_hlp.reference,'location_id':location_origen.id,'location_dest_id':location_destino.id,'quantity':move_line_hlp.quantity,'lot_id':pieza.id, 'company_id':2, 'product_uom_id':move_line_hlp.product_uom_id.id}) 
                move.state = 'done'
                if pieza.product_id.type == 'product':
                    self.env['stock.quant'].sudo().create({'product_id':pieza.product_id.id,'company_id':1,'owner_id':move_line_hlp.owner_id.id,'location_id':location_origen.id,'lot_id':move_line_hlp.lot_id.id,'quantity':-move_line_hlp.quantity})
                    self.env['stock.quant'].sudo().create({'product_id':pieza.product_id.id,'company_id':2,'owner_id':move_line_hlp.owner_id.id,'location_id':location_destino.id,'lot_id':pieza.id,'quantity':move_line_hlp.quantity})
        self.flag_moves_to_icarus = True


    def action_assign(self):
        result = super(StockPicking, self).action_assign()
        if result and self.is_instalacion:
            if len(self.move_line_ids_without_package) > 0:
                for item in self.move_line_ids_without_package:
                    if self.maintenance_request_id:
                        item.maintenance_request_id = self.maintenance_request_id.id
        return result

    def merge_pdfs(self, pdf_list):
        pdf_writer = PdfWriter()
        page_number = 1  # Inicializa el número de página

        for pdf_data in pdf_list:
            pdf_reader = PdfReader(io.BytesIO(pdf_data))
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                pdf_writer.add_page(page)

        # Crear un objeto BytesIO para almacenar el PDF combinado en memoria
        combined_pdf = io.BytesIO()
        pdf_writer.write(combined_pdf)

        # Posiciona el puntero al inicio del archivo
        combined_pdf.seek(0)
        return combined_pdf
    
    def print_etiquetas_all_lots(self):
        pdf_list = []
        for lot in self.rel_stock_production_lot:
            data = lot.get_data_report()
            # Asegura que el campo de imagen QR tenga el prefijo correcto
            if data.get('qr'):
                img_data = data['qr']
                if isinstance(img_data, bytes):
                    img_data = img_data.decode('utf-8')
                if not img_data.startswith('data:image'):
                    data['qr'] = f"data:image/png;base64,{img_data}"
                else:
                    data['qr'] = img_data
            report = self.env.ref('leulit_almacen.etiqueta_report')
            pdf_list.append(self.env['ir.actions.report']._render_qweb_pdf(report, lot, data=data)[0])

        self.etiquetas = base64.b64encode(self.merge_pdfs(pdf_list).getvalue())
        self.combined_pdf_filename = "Etiquetas {0}.pdf".format(self.name)
        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=stock.picking&id=" + str(self.id) + "&filename_field=combined_pdf_filename&field=etiquetas&download=true",
            'target': 'self'
        }
            

    rel_stock_production_lot = fields.One2many(compute="_get_stock_production_lot_from_stock_move_line",comodel_name="stock.lot",inverse_name="rel_stock_picking",string="Piezas", store=False)
    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order", domain=[('done','=',False)])
    equipment = fields.Many2one(related="maintenance_request_id.equipment_id", comodel_name="maintenance.equipment", string="Equipo Work Order")
    flag_moves_to_icarus = fields.Boolean(string="Movimientos hasta Icarus", default=False)
    owner_id = fields.Many2one(
        'res.partner', 'Assign Owner',
        check_company=True,
        help="When validating the transfer, the products will be assigned to this owner.",default=1)
    is_instalacion = fields.Boolean(compute="get_tipo_instalacion", string="¿Es instalacion?", store=False)
    etiquetas = fields.Binary()
    combined_pdf_filename = fields.Char()
    # repair_id = fields.Many2one(comodel_name="repair.order", string="Orden de Reparación")

    @api.depends('picking_type_id')
    def get_tipo_instalacion(self):
        tipo = self.env['stock.picking.type'].search([('name','=','Instalación')])
        for item in self:
            item.is_instalacion = False
            if item.picking_type_id.id == tipo.id:
                item.is_instalacion = True
    
        