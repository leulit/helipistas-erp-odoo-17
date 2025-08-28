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
import logging
_logger = logging.getLogger(__name__)

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

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