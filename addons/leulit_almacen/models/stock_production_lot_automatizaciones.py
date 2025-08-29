# -*- encoding: utf-8 -*-

from re import A
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import pytz
from odoo.addons.leulit import utilitylib
import threading
import time


_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _name = 'stock.lot'
    _inherit = 'stock.lot'


    def notify_expiration_date(self):
        template = self.env.ref('leulit_almacen.email_template_notify_expiration_date', raise_if_not_found=False)
        email_values = {}
        if template:
            now = datetime.now().date()
            for item in self.search([('fecha_caducidad','<=',now),('product_qty','>',0)]):
                email_values[item.name] = {
                    'qty': item.product_qty,
                    'fecha_caducidad': item.fecha_caducidad,
                }
            email_context = {
                'email_values': email_values,
                'values_flag': True if len(email_values) > 0 else False,
            }
            template.with_context(email_context).send_mail(self.env.user.id, force_send=True)