# -*- encoding: utf-8 -*-

from importlib.util import set_loader
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulitReunionTemplate(models.Model):
    _name = "leulit.reunion_template"
    _description = 'Plantilla de Reunión'

    name = fields.Char(string="Nombre", required=True)
    descripcion = fields.Html('Descripción',required=True)