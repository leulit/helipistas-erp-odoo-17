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


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"


    def notify_stock_minimo(self):
        template = self.env.ref('leulit_almacen.email_template_notify_stock_minimo', raise_if_not_found=False)
        email_values = {}
        if template:
            # _logger.error('template')
            for item in self.search([]):
                if item.qty_on_hand + item.qty_opcionales < item.product_min_qty:
                    name = '['+item.product_id.default_code+'] '+item.product_id.name
                    email_values[name] = {
                        'qty': item.qty_on_hand + item.qty_opcionales,
                        'min_qty': item.product_min_qty,
                    }
            email_context = {
                'email_values': email_values,
                'values_flag': True if len(email_values) > 0 else False,
            }
            template.with_context(email_context).send_mail(self.env.user.id, force_send=True)