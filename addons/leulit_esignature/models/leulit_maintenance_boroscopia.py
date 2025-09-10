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


class LeulitMaintenanceBoroscopia(models.Model):
    _name = "leulit.maintenance_boroscopia"
    _inherit = 'leulit.maintenance_boroscopia'


    def _esignature_docs(self):
        for item in self:
            docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_boroscopia'),('idmodelo','=',item.id)])
            if len(docs) > 0:
                item.esignature_docs = docs.ids
            else:
                item.esignature_docs = None
    

    esignature_docs = fields.One2many(compute=_esignature_docs, comodel_name='leulit_signaturedoc', string='Documentos firma', store=False)
    

    def set_estado_borrador(self):
        super(LeulitMaintenanceCRS, self).set_estado_borrador()
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_boroscopia'),('idmodelo','=',self.id)])
        docs.unlink()

    def getAllPendientesFirma(self):
        items = []
        if self.env.user.can_sign_boroscopia:
            for item in self.search([('estado','=','pendiente')], order= "fecha DESC"):
                items.append(item)
        return items

    def buildPdfSigned(self, datos, esignature):
        _logger.error('##############################    buildPdfSigned   -->  firmando boroscopia')
        for item in self:
            item.buildFirmarDocsOdoo(esignature, False)
            item.estado = 'firmado'

    def buildFirmarDocsOdoo(self, esignature, hack_firmado_por):
        _logger.error('##############################    buildFirmarDocsOdoo   -->  firmando boroscopia')
        for item in self:
            referencia = item.name
            self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.maintenance_boroscopia', item.name, referencia, item.fecha)
            
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
            _logger.error('##############################    generarPdfFirmado   -->  firmando boroscopia')
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.maintenance_boroscopia', item.id, item.name)
            if hack_firmado_por == False:
                firmado_por = self.env.user.name
                firmado_por_id = self.env.user.id
            else:
                firmado_por = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].name
                firmado_por_id = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].id

            datos = {
                'modelo': 'leulit.maintenance_boroscopia',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fecha,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,
                'hashcode' : hashcode,
                'referencia': item.name,
                'filename': '{0}.pdf'.format(item.name),
                'prefijo_hashcode': "BORO",
            }

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
                'hashcode_interno' : False,
                'hashcode' : hashcode,
                'firmado_por' : firmado_por,
                'logo_ica' : icarus_company.logo_reports if icarus_company.logo_reports else False,
                'num_pages' : len(boroscopialist)
            }
            pdf = self.env.ref('leulit_taller.leulit_20240214_0956_report')._render_qweb_pdf([],data=data)[0]
            report = base64.encodestring(pdf)
            datos.update({'report': report})
            return datos

    def firmar_boroscopias(self, fecha):
        _logger.error("################### firmar_boroscopias ")
        threaded_calculation = threading.Thread(target=self.run_firmar_boroscopias, args=([fecha]))
        _logger.error("################### firmar_boroscopias start thread")
        threaded_calculation.start()

    def run_firmar_boroscopias(self, fecha):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            boroscopias = self.env['leulit.maintenance_boroscopia'].with_context(context).sudo().search([('fecha','>=',fecha), ('estado', '=', 'firmado')])
            for boroscopia in boroscopias:
                boroscopia.esignature_docs.unlink()
                args={'otp':'123456',
                      'notp':'123456',
                      'modelo':'leulit.maintenance_boroscopia',
                      'idmodelo':boroscopia.id}
                context['args']=args
                user = False
                if boroscopia.mecanico:
                    user = self.env['res.users'].with_context(context).sudo().search([('partner_id','=',boroscopia.mecanico.getPartnerId())])

                self.env.uid = user.id if user else 14
                self.env['leulit_signaturedoc'].with_context(context).sudo().checksignatureRef()
                self.env.cr.commit()
        _logger.error('################### firmar_boroscopias fin thread')
