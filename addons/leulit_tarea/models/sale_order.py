# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class sale_order(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    
    account_analytic_line = fields.One2many(comodel_name='account.analytic.line', inverse_name='sale_order', string='Imputaciones de Tiempo')