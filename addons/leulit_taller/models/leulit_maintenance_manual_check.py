# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulitMaintenanceManualCheck(models.Model):
    _name           = "leulit.maintenance_manual_check"
    _description    = "leulit_maintenance_manual_check"


    check = fields.Date(string="Check")
    descripcion = fields.Char(string="Descripción")
    maintenance_manual_id = fields.Many2one(comodel_name="leulit.maintenance_manual", string="Manual")