# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64

_logger = logging.getLogger(__name__)


class LeulitAnotacionTechnicalLog(models.Model):
    _inherit = 'leulit.anotacion_technical_log'

    def getAllPendientesFirma(self):
        items = []
        if self.env.user.can_sign_anotacion:
            for item in self.env['leulit.anotacion_technical_log'].search([('check_firmado','=',False),('estado','not in',['pending','edition'])], order= "fecha DESC"):
                items.append(item)
        return items

    def prepareSignature(self, descripcion, referencia, modelo, idmodelo, fecha_firma):
        return self.env['leulit_signaturedoc'].prepareSignature( idmodelo, modelo, descripcion, referencia, fecha_firma)

    def buildFirmarDocsOdoo(self, esignature, hack_firmado_por):
        _logger.error('##############################    buildFirmarDocsOdoo   -->  firmando anotacion technical log')
        for item in self:
            referencia = 'LOG-[{0}]-{1}'.format(item.id, item.estado)
            self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.anotacion_technical_log', item.codigo, referencia, item.fecha)
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

    def buildPdfSigned(self, datos, esignature):
        _logger.error('##############################    buildPdfSigned   -->  firmando anotacion technical log')
        for item in self:
            item.buildFirmarDocsOdoo(esignature, False)
            item.check_firmado = True

    def generarPdfFirmado(self, esignature, hack_firmado_por):
        for item in self:
            _logger.error('##############################    generarPdfFirmado   -->  firmando anomalia')
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.anotacion_technical_log', item.id, "LOG-{0}".format(esignature))
            if hack_firmado_por == False:
                firmado_por = self.env.user.name
                firmado_por_id = self.env.user.id
            else:
                firmado_por = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].name
                firmado_por_id = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].id

            datos = {
                'modelo': 'leulit.anotacion_technical_log',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fecha_cierre,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,
                'hashcode' : hashcode,
                'referencia': 'LOG-[{0}]-{1}'.format(item.id, item.estado),
                'filename': 'LOG-[{0}]-{1}.pdf'.format(item.id, item.estado),
                'prefijo_hashcode': "LOG",
            }
            _ROL_MAP = {'1': 'Pilot', '2': 'Mechanic', '3': 'CAMO', '4': 'Others'}
            rol_informa = _ROL_MAP.get(item.rol_informa, '')
            rol_close = _ROL_MAP.get(item.rol_close, '')

            data = {
                'codigo' : item.codigo,
                'id' : item.id,
                'fecha' : item.fecha if item.fecha else "N/A",
                'informado_por' : item.informado_por.name if item.informado_por else "N/A",
                'rol_informa' : rol_informa,
                'lugar' : item.lugar if item.lugar else "N/A",
                'anotacion' : item.anotacion if item.anotacion else "N/A",

                'fecha_cierre' : item.fecha_cierre if item.fecha_cierre else "N/A",
                'cerrado_por' : item.cerrado_por.name if item.cerrado_por else "N/A",
                'cerrado_por_company' : item.company_id.name if item.company_id else "N/A",
                'rol_close' : rol_close,
                'accion_cierre' : item.accion_cierre if item.accion_cierre else "N/A",

                'fecha_crs' : item.fecha_crs if item.fecha_crs and rol_close == 'Mechanic' else False,
                'crs_por' : item.crs_por.name if item.crs_por and rol_close == 'Mechanic' else False,
                'lugar_crs' : item.lugar_crs if item.lugar_crs and rol_close == 'Mechanic' else False,
                'cas' : hashcode if hashcode and rol_close == 'Mechanic' else False,

                'helicoptero_id' : item.helicoptero_id.name if item.helicoptero_id else "N/A",
                'estado' : item.estado,
                'firmado_por' : firmado_por,
                'hashcode' : hashcode,
                'hashcode_interno' : item.codigo,
                'logo' : item.logo.decode() if item.logo else False,
            }
            report = self.env.ref('leulit_seguridad.leulit_20260414_1111_imprimir_anotacion_technical_log')
            pdf = self.env['ir.actions.report']._render_qweb_pdf(report,[],data=data)[0]
            report = base64.b64encode(pdf)
            datos.update({'report': report})
            return datos
        
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'LOG-%s' % (self.codigo)

    def _esignature_docs(self):
        for item in self:
            docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.anotacion_technical_log'),('idmodelo','=',item.id)])
            if len(docs) > 0:
                item.esignature_docs = docs.ids
            else:
                item.esignature_docs = None

    def _semaforo_firma(self):
        for item in self:
            if item.fecha > datetime(2020, 9, 11).date():            
                valor = 'red'                
                docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.anotacion_technical_log'),('idmodelo','=',item.id)])
                for signaturedoc in docs:
                    if signaturedoc.estado == signaturedoc.COMPLETADO:
                        valor = 'green'
                item.semaforo_firma = valor
            else:
                item.semaforo_firma = "N.A."

    def get_anotaciones_unsigned_by_helicoptero(self, helicoptero_id):
        return self.search([('helicoptero_id','=',helicoptero_id),('check_firmado','=',False),('estado', '!=', 'edition')])

    def haveNoGo(self, helicoptero_id, fecha):
        nitems = self.search_count([('fecha','<=',fecha),('helicoptero_id','=',helicoptero_id),('check_firmado','=',False),('estado', '!=', 'edition')])
        return nitems > 0

    esignature_docs = fields.One2many(compute=_esignature_docs, comodel_name='leulit_signaturedoc', string='Documentos firma', store=False)
    semaforo_firma = fields.Char(compute=_semaforo_firma, store=False, string='Semáforo')
    check_firmado = fields.Boolean(string="Anotación firmada", default=False)