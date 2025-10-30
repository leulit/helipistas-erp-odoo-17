# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_mel_tipo_operacion(models.Model):
    _name           = "leulit.mel_tipo_operacion"
    _description    = "leulit_mel_tipo_operacion"
    
    
    name = fields.Char('Descripción',required=True)
    