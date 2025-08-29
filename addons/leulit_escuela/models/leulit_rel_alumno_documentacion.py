# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_rel_alumno_documentacion(models.Model):
    _name = "leulit.rel_alumno_documentacion"
    _description = "leulit_rel_alumno_documentacion"
    

    alumno_id = fields.Many2one('leulit.alumno', 'Alumno', required=True)
    name = fields.Char("Nombre", required=True)
    fecha_expedicion = fields.Date("Fecha expedición", required=False)
    fecha_validez = fields.Date("Fecha validez", required=False)
    doc_alumno = fields.Many2many('ir.attachment', 'leulit_alumno_rel','alumno_rel','doc_rel','Documentos')

