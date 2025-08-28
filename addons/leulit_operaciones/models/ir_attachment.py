# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class ir_attachment(models.Model):
    _inherit = 'ir.attachment'
    
    piloto_adjunto_id = fields.Many2one('leulit.piloto_adjunto', 'Piloto adjunto id')
