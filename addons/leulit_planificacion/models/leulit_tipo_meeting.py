# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_tipo_meeting(models.Model):
    _name = 'leulit.tipo_meeting'
    _description = 'leulit_tipo_meeting'

    name = fields.Char('Descripción', size=255)
    reunion_id = fields.Many2one('calendar.event', 'Reunión')
