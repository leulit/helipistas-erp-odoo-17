# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_analisis_aceite(models.Model):
    _name = "leulit.analisis_aceite"
    _description = "leulit_analisis_aceite"
    _rec_name = "n_muestra"
    _order = "n_muestra desc"



    n_muestra = fields.Char('Nº Muestra', required=True)
    descripcion = fields.Char('Descripción')
    # work_order = fields.Many2one('leulit.work_order', 'Work order')
    attachment_ids = fields.Many2many('ir.attachment', 'analisis_aceite_ir_attachments_rel', 'analisis_aceite_id','attachment_id','Adjuntos')
    comentarios = fields.Html('Comentarios')
