# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceBoroscopia(models.Model):
    _inherit = 'leulit.maintenance_boroscopia'


    herramienta_ids = fields.Many2many('stock.lot', 'rel_boroscopia_lot' , 'boroscopia_id' ,'stock_production_lot_id' ,'Herramientas')
