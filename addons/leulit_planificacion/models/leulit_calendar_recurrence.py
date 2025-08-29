# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
import pytz

from dateutil import rrule
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.base.models.res_partner import _tz_get

class RecurrenceRule(models.Model):
    _name = 'calendar.recurrence'
    _inherit = 'calendar.recurrence'


    dtstop = fields.Datetime(compute='_compute_dtstop')

    @api.depends('calendar_event_ids.stop')
    def _compute_dtstop(self):
        groups = self.env['calendar.event'].read_group([('recurrence_id', 'in', self.ids)], ['stop:max'], ['recurrence_id'])
        start_mapping = {
            group['recurrence_id'][0]: group['stop']
            for group in groups
        }
        for recurrence in self:
            recurrence.dtstop = start_mapping.get(recurrence.id)
