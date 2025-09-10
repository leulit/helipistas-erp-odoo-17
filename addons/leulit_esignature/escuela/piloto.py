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


class leulit_piloto(models.Model):
    _inherit = "leulit.piloto"


    def buildDocPerfilFormacionFirmado1Step(self, descripcion, fecha, report, hashcode):        
        for item in self:
            datos = {
                'modelo': 'leulit.piloto',
                'idmodelo': item.id,
                'otp': "N.A.",
                'fecha_firma': fecha
            }
            import uuid
            uuid = uuid.uuid4().hex
            #INFORME PERFIL FORMACIÓN
            #if estado=='prevuelo':
            referencia ="{0}-{1}-PEF".format(item.id, uuid)
            self.prepareSignature(descripcion, referencia, datos)
            context = {}
            context.update({'hashcode': hashcode})        
            context.update({'report': report})
            iddoc = self.env['leulit_signaturedoc'].notchecksignature(datos, referencia)
            return iddoc
        

    def prepareSignature(self, descripcion, referencia):
        #self.prepareSignature(cr, uid, ids, { 'estado' : 'closed', 'name': 'anomalia - closed', 'idmodelo': ids, 'modelo': 'leulit.anomalia'})
        return self.pool['leulit_signaturedoc'].prepareSignature(context['modelo'], descripcion, referencia)



    def generarPdfFirmado(self, idModelo, fecha_firma, firma):
        context = {}
        usuario_name = self.pool.get('res.users').browse(cr, uid, uid).name
        context['usuario'] = usuario_name
        context['fecha_firma'] = utilitylib.formatFecha(fecha_firma, formatOrigen = utilitylib.STD_DATETIME_FORMAT, formatDestino = utilitylib.ESP_DATE_FORMAT)
        context['firma'] = firma
        context['estado'] = ""
        report = context['report']
        return [{'result'    : [report],'hashcode'  : context['hashcode']}]
