# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64
import json
import io
import pyqrcode

_logger = logging.getLogger(__name__)


class EsignatureWizard(models.TransientModel):
    _name = "leulit_esignaturewizard"
    _description = "leulit_esignaturewizard"

    def prepareSignature(self, idmodelo, model, descripcion, referencia, context=None):
        otp = self.env['res.users'].get_otp()
        mensaje = descripcion
        otp_qr = {
            'modelo': model,
            'idmodelo': idmodelo,
            'otp': otp,
            'reportname': ""
        }
        otp_qrstr = json.dumps(otp_qr)
        esignature = self.pool['res.users'].hashEncodeWithSecret(otp_qrstr)
        iddoc = self.pool['leulit_signaturedoc'].crearNuevo({
            'name' : mensaje,
            'modelo' : model,
            'idmodelo' : idmodelo,
            'esignature' : esignature
        })
        buffer = io.BytesIO()
        otp_qr['esignature'] = esignature
        otp_qr['mensaje'] = mensaje
        qrtext = json.dumps(otp_qr)
        qr = pyqrcode.create(qrtext)
        qr.png(buffer,scale=3) 
        binary = buffer.getvalue().encode('base64')

        context['default_modelo'] = model
        context['default_method'] = method
        context['default_idmodelo'] = idmodelo
        context['default_otp_qrcode'] = binary
        context['default_otp'] = otp
        context['default_qrtext'] = qrtext

        return {
            'type': 'ir.actions.act_window',
            'name': 'Validate e-signature',
            'res_model': 'leulit_esignaturewizard',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }





    modelo = fields.Char("Modelo")
    method = fields.Char("Método")
    idmodelo = fields.Char("Id modelo")
    fecha = fields.Char("Fecha")
    otp = fields.Char('Código')
    otp_qrcode = fields.Binary(string="QR")
    qrtext = fields.Char('Cadena QR')

