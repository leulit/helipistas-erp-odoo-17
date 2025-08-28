# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceBoroscopia(models.Model):
    _name = "leulit.maintenance_boroscopia"
    _rec_name = "name"
    _inherit = ['mail.thread']
    _order = "fecha desc"


    @api.depends('request','task')
    def get_name(self):
        for item in self:
            item.name = 'BORO'
            if item.task:
                item.name = 'BORO-'+item.request.name+'-'+item.task.name
            else:
                item.name = 'BORO-'+item.request.name

    @api.depends('form_one_ids')
    def _get_flag_form_one(self):
        for item in self:
            item.flag_form_one = False
            if len(item.form_one_ids) > 0:
                item.flag_form_one = True


    name = fields.Char(compute=get_name, string="Nombre")
    # fecha_boroscopia = fields.Date(string="Fecha")
    tsn = fields.Float(string="TSN")
    request = fields.Many2one(comodel_name="maintenance.request", string="Orden de trabajo")
    plan = fields.Many2one(related="request.maintenance_plan_id", string="Plan de mantenimiento")
    helicoptero = fields.Many2one(related="request.equipment_id.helicoptero", string="Helicóptero")
    modelo = fields.Many2one(related="request.equipment_id.helicoptero.modelo", string="Modelo")
    fabricante = fields.Selection(related="request.equipment_id.helicoptero.fabricante", string="Fabricante")
    serialnum = fields.Char(related="request.equipment_id.helicoptero.serialnum", string="Número de serie")
    lugar = fields.Char(string="Lugar", default="LEUL")
    fecha = fields.Date(string="Fecha", default=fields.Date.context_today)
    mecanico = fields.Many2one(comodel_name="leulit.mecanico", string="Técnico")
    estado = fields.Selection([('borrador', 'Borrador'),('pendiente', 'Pendiente Firma'),('firmado','Firmado')], string='Estado', default="borrador")
    herramienta_ids = fields.Many2many('stock.lot', 'rel_boroscopia_lot' , 'boroscopia_id' ,'stock_production_lot_id' ,'Herramientas')
    task = fields.Many2one(comodel_name="project.task", domain="[('maintenance_request_id','=',request)]", string="Tarea")
    resultado_inspeccion = fields.Text(string="Resultado de la inspección")
    form_one_ids = fields.One2many(comodel_name="leulit.maintenance_form_one", inverse_name="boroscopia_id", string="Form One")
    flag_form_one = fields.Boolean(compute=_get_flag_form_one, string="Create Form One")


    def create_form_one_from_boroscopia(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230706_1118_form')
        view_id = view_ref and view_ref[1] or False
        
        form_one_today = self.env['leulit.maintenance_form_one'].search([('fecha','=',datetime.now().date())])
        sequence = 1
        if len(form_one_today) > 0:
            sequence = len(form_one_today)+1
        name = 'ICM-'+datetime.now().strftime("%y%m%d")+'-'+str(sequence)

        form_one = self.env['leulit.maintenance_form_one'].create({
            'tracking_number': name,
            'work_order_id': self.request.id,
            'boroscopia_id': self.id,
            'fecha': self.fecha,
            'certificador': self.mecanico.id,
            'task_id': self.task.id,
            'status_work': 'inspected_tested',
            'remarks': '<b>Informe de Boroscopia: </b>'+self.name+'<br/><br/><b>Resultado de la Inspección:</b><br/>'+self.resultado_inspeccion
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Form One',
            'res_model': 'leulit.maintenance_form_one',
            'view_mode': 'form',
            'res_id': form_one.id,
            'view_id': view_id,
            'target': 'current',
        }

    def set_estado_firmado_boroscopia(self):
        self.estado = "firmado"

    def set_estado_borrador_boroscopia(self):
        self.estado = "borrador"

    def set_estado_pendiente_firma_boroscopia(self):
        self.estado = "pendiente"

    def comprobar_estado_wo_boroscopia(self, request):
        """Comprueba si existen Boroscopias sin firmar de la orden de trabajo"""
        for item in self.search([('request','=',request)]):
            if item.estado != 'firmado':
                raise UserError('No puede cerrar esta Orden de Trabajo porque tiene una/s Boroscopias sin firmar.')
        return True

    def edit_boroscopia(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20240212_1600_form')
        view_id = view_ref and view_ref[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Boroscopia',
            'res_model': 'leulit.maintenance_boroscopia',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': view_id,
            'target': 'current',
        }

    def print_boroscopia(self):
        data = self._get_data_to_print_boroscopia()
        return self.env.ref('leulit_taller.leulit_20240214_0956_report').report_action(self, data=data)
    
    def _get_data_to_print_boroscopia(self):
        boroscopialist = []
        icarus_company = self.env['res.company'].search([('name','=','Icarus Manteniment S.L.')])
        hashcode_interno = ''
        for item in self:
            herramientas = []
            for tool in item.herramienta_ids:
                herramientas.append({
                    'pn': tool.product_id.default_code,
                    'sn': tool.sn,
                    'fabricante': tool.fabricante,
                })
            boroscopia = {
                'matricula': item.helicoptero.name,
                'marca': item.helicoptero.descfabricante,
                'modelo': item.modelo.name,
                'sn': item.serialnum,
                'tsn': round(item.tsn,2),
                'ot': item.request.name,
                'plan': item.plan.name,
                'resultado_inspeccion': item.resultado_inspeccion,
                'name': item.name,
                'lugar': item.lugar,
                'certificador': item.mecanico.name,
                'fecha': item.fecha,
                'firma': item.mecanico.firma,
                'sello': item.mecanico.sello,
                'herramientas': herramientas,
                }
            docref = datetime.now().strftime("%Y%m%d")
            hashcode_interno = utilitylib.getHashOfData(docref)
            boroscopialist.append(boroscopia)
        data = {
            'boroscopialist' : boroscopialist,
            'hashcode_interno' : hashcode_interno,
            'hashcode' : False,
            'firmado_por' : False,
            'logo_ica' : icarus_company.logo_reports if icarus_company.logo_reports else False,
            'num_pages' : len(boroscopialist)
        }
        return data