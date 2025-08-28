# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_vuelo_tipo_line(models.Model):
    _name = "leulit.vuelo_tipo_line"
    _description = "leulit_vuelo_tipo_line"
    _rec_name = "vuelo_tipo_id"

    vuelo_id = fields.Many2one('leulit.vuelo', 'Referencia vuelo', required=True, select=True)
    vuelo_tipo_id = fields.Many2one('leulit.vuelostipo', 'Tipo vuelo', required=True)
    privado = fields.Boolean('Privado',help="Indica si el tipo de vuelo será visible en los documentos oficiales")
    