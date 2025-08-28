# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_ficha_datos_seguridad(models.Model):
    _name = "leulit.ficha_datos_seguridad"
    _description = "leulit_ficha_datos_seguridad"
    _rec_name = "producto"
    _order = "producto"


    producto = fields.Char('Producto', required=True)
    fecha = fields.Date('Fecha de revisión')
    version = fields.Char('Versión')
    proveedor = fields.Char('Proveedor')
    attachment_ids = fields.Many2many('ir.attachment', 'ficha_datos_seguridad_ir_attachments_rel', 'ficha_datos_seguridad_id','attachment_id','Adjuntos')
    observaciones = fields.Text('Observaciones')