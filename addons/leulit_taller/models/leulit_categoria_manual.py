# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_categoria_manual(models.Model):
    _name           = "leulit.categoria_manual"
    _description    = "leulit_categoria_manual"

    name = fields.Char(string="Nombre")