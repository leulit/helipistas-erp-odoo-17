# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class res_company(models.Model):
    _name = "res.company"
    _inherit = "res.company"


    watermark = fields.Binary(string="Marca de agua")
    logo_reports = fields.Binary(string="Logo para informes")