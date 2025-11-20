# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
import base64
import threading
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceCRS(models.Model):
    _name = "leulit.maintenance_crs"
    _inherit = 'leulit.maintenance_crs'


    def _esignature_docs(self):
        for item in self:
            docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_crs'),('idmodelo','=',item.id)])
            if len(docs) > 0:
                item.esignature_docs = docs.ids
            else:
                item.esignature_docs = None
    

    esignature_docs = fields.One2many(compute=_esignature_docs, comodel_name='leulit_signaturedoc', string='Documentos firma', store=False)
    

    def set_estado_borrador(self):
        super(LeulitMaintenanceCRS, self).set_estado_borrador()
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_crs'),('idmodelo','=',self.id)])
        docs.unlink()

    def getAllPendientesFirma(self):
        items = []
        if self.env.user.can_sign_crs:
            for item in self.search([('estado','=','pendiente')], order= "fecha DESC"):
                items.append(item)
        return items

    def buildPdfSigned(self, datos, esignature):
        _logger.error('##############################    buildPdfSigned   -->  firmando crs')
        for item in self:
            item.buildFirmarDocsOdoo(esignature, False)
            item.set_estado_firmado()

    def buildFirmarDocsOdoo(self, esignature, hack_firmado_por):
        _logger.error('##############################    buildFirmarDocsOdoo   -->  firmando crs')
        for item in self:
            referencia = item.n_cas
            self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.maintenance_crs', item.n_cas, referencia, item.fecha)
            
            datospdf = self.generarPdfFirmado( esignature, hack_firmado_por )
            for item2 in self.env['leulit_signaturedoc'].search([('referencia', '=', referencia)]):
                attach_id = self.env['ir.attachment'].create({
                    'name': datospdf['filename'],
                    'type': 'binary',
                    'datas': datospdf['report'],
                    'res_model': "leulit_signaturedoc",
                    'res_id': item2.id,
                    'public': True
                })
                datosdb = {
                    'attachment_id' : attach_id,
                    'estado' : item2.COMPLETADO,
                    'hashcode' : datospdf['hashcode'],
                    'esignature' : datospdf['esignature'],
                }
                item2.write(datosdb)

    def generarPdfFirmado(self, esignature, hack_firmado_por):
        for item in self:
            _logger.error('##############################    generarPdfFirmado   -->  firmando crs')
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.maintenance_crs', item.id, item.n_cas)
            if hack_firmado_por == False:
                firmado_por = self.env.user.name
                firmado_por_id = self.env.user.id
            else:
                firmado_por = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].name
                firmado_por_id = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].id

            datos = {
                'modelo': 'leulit.maintenance_crs',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fecha,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,
                'hashcode' : hashcode,
                'referencia': item.n_cas,
                'filename': '{0}.pdf'.format(item.n_cas),
                'prefijo_hashcode': "CAS",
            }

            crslist = []
            icarus_company = self.env['res.company'].search([('name','=','Icarus Manteniment S.L.')])
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
            crslist.append(crs)
            data = {
                'crslist' : crslist,
                'hashcode_interno' : False,
                'hashcode' : hashcode,
                'firmado_por' : firmado_por,
                'logo_ica' : icarus_company.logo_reports if icarus_company.logo_reports else False,
                'num_pages' : len(crslist)
            }
            report = self.env.ref('leulit_taller.leulit_20230707_1128_report')
            pdf = self.env['ir.actions.report']._render_qweb_pdf(report,[],data=data)[0]
            report = base64.b64encode(pdf)
            datos.update({'report': report})
            return datos


    def firmar_crs(self, fecha):
        _logger.error("################### firmar_crs ")
        threaded_calculation = threading.Thread(target=self.run_firmar_crs, args=([fecha]))
        _logger.error("################### firmar_crs start thread")
        threaded_calculation.start()

    def run_firmar_crs(self, fecha):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            crss = self.env['leulit.maintenance_crs'].with_context(context).sudo().search([('fecha','>=',fecha), ('estado', '=', 'firmado')])
            for crs in crss:
                crs.esignature_docs.unlink()
                args={'otp':'123456',
                      'notp':'123456',
                      'modelo':'leulit.maintenance_crs',
                      'idmodelo':crs.id}
                context['args']=args
                user = False
                if crs.certificador:
                    user = self.env['res.users'].with_context(context).sudo().search([('partner_id','=',crs.certificador.getPartnerId())])

                self.env.uid = user.id if user else 14
                self.env['leulit_signaturedoc'].with_context(context).sudo().checksignatureRef()
                self.env.cr.commit()
        _logger.error('################### firmar_crs fin thread')
