# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'


    rotable_lifelimit = fields.Boolean(string="Rotable/Life Limit")
    is_motor = fields.Boolean(string="Motor")
    tipo_motor = fields.Selection(selection=[('piston', 'Pistón'),('turbina', 'Turbina')], string="Tipo motor")
