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


class leulit_alumno(models.Model):
    _inherit = "leulit.alumno"
    
    def buildDocTeoricasFirmado1Step(self, descripcion, fecha, report, hashcode):        
        for item in self:
            datos = {
                'modelo': 'leulit.alumno',
                'idmodelo': item.id,
                'otp': "N.A.",
                'fecha_firma': fecha,
                'report' : report,
                'hashcode' : hashcode,
            }
            import uuid
            uuid = uuid.uuid4().hex
            #INFORME CLASES TEÓRICAS
            #if estado=='prevuelo':
            referencia ="{0}-{1}-ESC_ALU_TE".format(item.id, uuid)
            self.prepareSignature(descripcion, referencia, 'leulit.alumno', item.id, fecha)
            
            '''
            context = {}
            context.update({'hashcode': hashcode})        
            context.update({'report': report})
            '''

            iddoc = self.env['leulit_signaturedoc'].notchecksignature(datos, referencia)
            return iddoc


    def buildDocPracticasFirmado1Step(self, idalumno, descripcion, fecha, report, hashcode):
        for item in self.search([('id','=',idalumno)]):
            datos = {
                'modelo': 'leulit.alumno',
                'idmodelo': item.id,
                'otp': "N.A.",
                'fecha_firma': fecha,
                'report' : report,
                'hashcode' : hashcode,
            }
            import uuid
            uuid = uuid.uuid4().hex
            referencia ="{0}-{1}-ESC_ALU_PR".format(item.id, uuid)
            self.prepareSignature(descripcion, referencia, 'leulit.alumno', item.id, fecha)
            context = {}                   
            context.update({'hashcode': hashcode})        
            context.update({'report': report})
            iddoc = self.env['leulit_signaturedoc'].with_context(context).notchecksignature( datos, referencia )
            return iddoc

        
        

    def prepareSignature(self, descripcion, referencia, modelo, idmodelo, fecha_firma ):
        return self.env['leulit_signaturedoc'].prepareSignature( idmodelo, modelo, descripcion, referencia, fecha_firma)



    def generarPdfFirmado(self, idModelo, fecha_firma, firma, context=None):
        if context is None:
            context = {}
        usuario_name = self.pool.get('res.users').browse(self.env.uid).name
        context['usuario'] = usuario_name
        context['fecha_firma'] = utilitylib.formatFecha(fecha_firma, formatOrigen = utilitylib.STD_DATETIME_FORMAT, formatDestino = utilitylib.ESP_DATE_FORMAT)
        context['firma'] = firma
        context['estado'] = ""
        report = context['report']
        return [{'result'    : [report],'hashcode'  : context['hashcode']}]
