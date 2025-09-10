# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class ir_attachment(models.Model):
    _inherit = 'ir.attachment'
    
    rel_verification_line = fields.Many2one('mgmtsystem.verification.line', 'Rel Verification Line')
