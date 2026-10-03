# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AuthTotpDevice(models.Model):
    _inherit = "auth_totp.device"

    def _check_credentials_for_uid(self, *, scope, key, uid):
        # Sin dispositivos de confianza: el código del autenticador se pide en
        # cada login. Una cookie td_id antigua (90 días) ya no salta el paso.
        if scope == 'browser':
            return False
        return super()._check_credentials_for_uid(scope=scope, key=key, uid=uid)

    @api.model
    def _leulit_purge_browser_devices(self):
        self.env.cr.execute("DELETE FROM auth_totp_device WHERE scope = 'browser'")
        _logger.info("2FA: eliminados %d dispositivos de confianza", self.env.cr.rowcount)
