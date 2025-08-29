# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

from odoo.loglevels import exception_to_unicode
import requests
from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService, InvalidSyncToken


class res_users(models.Model):
    _inherit = "res.users"


    def _sync_google_calendar_leulit(self, calendar_service: GoogleCalendarService):
        self.ensure_one()
        full_sync = not bool(self.google_calendar_sync_token)
        with google_calendar_token(self) as token:
            try:
                events, next_sync_token, default_reminders = calendar_service.get_events(self.google_calendar_sync_token, token=token)
            except InvalidSyncToken:
                events, next_sync_token, default_reminders = calendar_service.get_events(token=token)
                full_sync = True
        self.google_calendar_sync_token = next_sync_token

        # Google -> Odoo
        events.clear_type_ambiguity(self.env)
        recurrences = events.filter(lambda e: e.is_recurrence())
        synced_recurrences = self.env['calendar.recurrence']._sync_google2odoo(recurrences)
        synced_events = self.env['calendar.event']._sync_google2odoo(events - recurrences, default_reminders=default_reminders)

        # Odoo -> Google
        recurrences = self.env['calendar.recurrence']._get_records_to_sync(full_sync=full_sync)
        recurrences -= synced_recurrences
        recurrences._sync_odoo2google(calendar_service)
        synced_events |= recurrences.calendar_event_ids - recurrences._get_outliers()
        events = self.env['calendar.event']._get_records_to_sync(full_sync=full_sync)
        (events - synced_events)._sync_odoo2google(calendar_service)

        return bool(events | synced_events) or bool(recurrences | synced_recurrences)
        # return bool(events | synced_events)

    @api.model
    def _sync_all_google_calendar_leulit(self):
        """ Cron job """
        users = self.env['res.users'].search([('google_calendar_rtoken', '!=', False)])
        google = GoogleCalendarService(self.env['google.service'])
        for user in users:
            _logger.info("Calendar Synchro - Starting synchronization for %s", user)
            try:
                user.with_user(user).sudo()._sync_google_calendar_leulit(google)
            except Exception as e:
                _logger.exception("[%s] Calendar Synchro - Exception : %s !", user, exception_to_unicode(e))

    


    
