# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitActividadAereaNoIntroducida(models.Model):
    _name = "leulit.actividad_aerea_no_introducida"
    _description = 'Actividad Aérea No Introducida en el Sistema'

    fecha = fields.Date(string="Fecha", required=True)