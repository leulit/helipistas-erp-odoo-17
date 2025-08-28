# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceCRS(models.Model):
    _name = "leulit.maintenance_crs"
    _rec_name = "n_cas"
    _inherit = ['mail.thread']
    _order = "fecha desc"


    @api.depends('request')
    def _get_ref_em(self):
        for item in self:
            item.ref_em = 'EM'+item.request.name

    @api.depends('helicoptero','fecha','tipo_crs')
    def _get_n_cas(self):
        for item in self:
            if item.helicoptero:
                partes = item.helicoptero.name.split("-")
                name = partes[1]
            else:
                name = 'XXX'
            item.n_cas = 'CAS'+name+item.fecha.strftime("%y%m%d")
            if item.tipo_crs:
                if item.tipo_crs == 'completo':
                    item.n_cas += '-C'
                else:
                    item.n_cas += '-I'
            if item.rev:
                item.n_cas += '-'+item.rev
    
    @api.constrains("helicoptero","fecha","tipo_crs")
    def _check_n_cas_from_others(self):
        for crs in self:
            query = self.search([('helicoptero','=',crs.helicoptero.id),('fecha','=',crs.fecha),('tipo_crs','=',crs.tipo_crs),('id','!=',crs.id),('rev','=',crs.rev)])
            if len(query) > 0:
                raise ValidationError("Ya existe otro CRS con el mismo Nº del CAS/CRS.")
    
    @api.depends('request')
    def _get_motor(self):
        for item in self:
            motor = item.request.equipment_id.get_motor()
            item.motor = False
            item.marca_motor = '-'
            if motor:
                item.motor = motor.production_lot.id
                item.marca_motor = motor.marca_motor

    fecha_crs = fields.Date(string="Fecha")
    horas_crs = fields.Float(string="TSN Aeronave")
    tso_crs = fields.Char(string="TSO Aeronave")
    motor = fields.Many2one(compute=_get_motor, comodel_name="stock.lot", string="Motor")
    marca_motor = fields.Char(compute=_get_motor, string="Fabricante")
    tsn_motor = fields.Float(string="TSN Motor")
    tsn_motor_str = fields.Char(string="TSN Motor")
    tso_motor = fields.Char(string="TSO Motor")
    tso_motor_str = fields.Char(string="TSO Motor")
    request = fields.Many2one(comodel_name="maintenance.request", string="Orden de trabajo")
    plan = fields.Many2one(related="request.maintenance_plan_id", string="Plan de mantenimiento")
    helicoptero = fields.Many2one(related="request.equipment_id.helicoptero", string="Helicóptero")
    modelo = fields.Many2one(related="request.equipment_id.helicoptero.modelo", string="Modelo")
    fabricante = fields.Selection(related="request.equipment_id.helicoptero.fabricante", string="Fabricante")
    serialnum = fields.Char(related="request.equipment_id.helicoptero.serialnum", string="Número de serie")
    ref_em = fields.Char(compute=_get_ref_em, string="Ref. EM. / W. Pack")
    limitaciones = fields.Many2one(comodel_name="leulit.limitaciones_aeronavegabilidad", string="Limitaciones de aeronavegabilidad u operacionales")
    tipo_crs = fields.Selection(selection=[('completo','Completo'),('incompleto','Incompleto')], string="Tipo de CAS/CRS")
    n_cas = fields.Char(compute=_get_n_cas, string="Nº del CAS/CRS")
    lugar = fields.Char(string="Lugar", default="LEUL")
    fecha = fields.Date(string="Fecha", default=fields.Date.context_today)
    certificador = fields.Many2one(comodel_name="leulit.mecanico", string="Técnico Certificador", domain=[('certificador','=',True)])
    tareas = fields.Text(string="Detalles de trabajo")
    estado = fields.Selection([('borrador', 'Borrador'),('pendiente', 'Pendiente Firma'),('firmado','Firmado')], string='Estado', default="borrador")
    rev = fields.Char(string="Rev.", default="")
    
    def wizard_send_email(self):
        context = self.env.context.copy()
        context.update({'subject': u' Se ha firmado el CRS ({0})'.format(self.n_cas)})
        emails=['erpanomalias@helipistas.com', 'otecnica@helipistas.com']
        for emailto in emails:
            context.update({'mail_to': emailto})
            template = self.with_context(context).env.ref("leulit_taller.leulit_mail_camo_crs_firmado")
            try:
                template.send_mail(self.id, force_send=True, raise_exception=True)
            except Exception as e:
                pass
    
    def set_estado_borrador(self):
        self.estado = 'borrador'

    def set_estado_firmado(self):
        for task in self.request.task_ids:
            task.supervisado_por = self.certificador.id
        self.estado = 'firmado'
        self.wizard_send_email()
        

    def set_estado_pendiente_firma(self):
        mecanico_user = self.env['leulit.mecanico'].search([('partner_id','=',self.env.user.partner_id.id)])
        if mecanico_user.id != self.certificador.id:
            raise UserError('Solo el técnico certificador puede firmar esta orden de trabajo.')
        self.estado = 'pendiente'

    def comprobar_estado_wo_crs(self, request):
        """Comprueba si existen CRS sin firmar de la orden de trabajo"""
        for item in self.search([('request','=',request)]):
            if item.estado != 'firmado':
                raise UserError('No puede cerrar esta Orden de Trabajo porque tiene un/os CRS sin firmar.')
        return True
        

    def edit_crs(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230623_1633_form')
        view_id = view_ref and view_ref[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRS',
            'res_model': 'leulit.maintenance_crs',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': view_id,
            'target': 'current',
        }

    def print_crs(self):
        data = self._get_data_to_print_crs()
        return self.env.ref('leulit_taller.leulit_20230707_1128_report').report_action(self, data=data)
    
    
    def _get_data_to_print_crs(self):
        crslist = []
        icarus_company = self.env['res.company'].search([('name','=','Icarus Manteniment S.L.')])
        hashcode_interno = ''
        for item in self:
            tipo_crs = ''
            if item.tipo_crs == 'completo':
                tipo_crs = 'Completo'
            if item.tipo_crs == 'incompleto':
                tipo_crs = 'Incompleto'
            
            motor = item.request.equipment_id.get_motor()
            crs = {
                'matricula': item.helicoptero.name,
                'marca_aeronave': item.helicoptero.descfabricante.capitalize(),
                'modelo_aeronave': item.modelo.name,
                'sn_aeronave': item.serialnum,
                'tsn_aeronave': round(item.horas_crs,2),
                'tso_aeronave': item.tso_crs,
                'marca_motor': motor.marca_motor if motor else '-',
                'modelo_motor': motor.production_lot.product_id.default_code if motor else '-',
                'sn_motor': motor.production_lot.sn if motor else '-',
                'tsn_motor': round(item.tsn_motor,2) if item.motor else item.tsn_motor_str,
                'tso_motor': item.tso_motor if item.motor else item.tso_motor_str,
                'ot': item.request.name,
                'plan': item.plan.name if item.plan else item.request.referencia_programa_mantenimiento,
                'tareas': item.tareas,
                'limitaciones': item.limitaciones.name,
                'tipo_crs': tipo_crs,
                'n_cas': item.n_cas,
                'lugar': item.lugar,
                'certificador': item.certificador.name,
                'ref_em': item.ref_em,
                'fecha': item.fecha,
                'firma': item.certificador.firma,
                'sello': item.certificador.sello,
                }
            docref = datetime.now().strftime("%Y%m%d")
            hashcode_interno = utilitylib.getHashOfData(docref)
            crslist.append(crs)
        data = {
            'crslist' : crslist,
            'hashcode_interno' : hashcode_interno,
            'hashcode' : False,
            'firmado_por' : False,
            'logo_ica' : icarus_company.logo_reports if icarus_company.logo_reports else False,
            'num_pages' : len(crslist)
        }
        return data


    def _get_report_filename(self, report_name):
        self.ensure_one()
        return "{}_{}".format(self.name, self.id)