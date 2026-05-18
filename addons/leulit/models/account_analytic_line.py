# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
import pytz
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp
import threading
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"


    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        domain="[('category_id', '=', product_uom_category_id)]",
        default=4,
    )

    @api.depends("date_time", "unit_amount")
    def _compute_date_time_end(self):
        for record in self:
            if record.date_time and record.unit_amount:
                record.date_time_end = record.date_time + relativedelta(hours=record.unit_amount)
            else:
                record.date_time_end = record.date_time_end

    def get_date_time_int(self):
        if self.date_time:
            return int(self.date_time.astimezone(pytz.timezone("Europe/Madrid")).strftime("%H%M%S"))
        else:
            return False

    def get_date_time_end_int(self):
        if self.date_time_end:
            return int(self.date_time_end.astimezone(pytz.timezone("Europe/Madrid")).strftime("%H%M%S"))
        else:
            return False

