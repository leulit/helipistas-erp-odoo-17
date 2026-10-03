# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons.base.models.res_users import check_identity

_logger = logging.getLogger(__name__)


class res_users(models.Model):
    _name = "res.users"
    _inherit = "res.users"


    def get_partner(self):
        return self.env.user.partner_id

    def get_user_by_partner(self, partner_id):
        return self.search([('partner_id','=',partner_id)])

    def _mfa_type(self):
        # 2FA obligatoria para todos los usuarios, sin excepción: si nadie
        # más arriba en la cadena (auth_totp, oauth...) ya exige un segundo
        # factor, lo exigimos nosotros. Si el usuario aún no tiene la app
        # configurada (totp_enabled=False), auth_totp igualmente delega aquí
        # (devuelve None) y seguimos mandándolo por /web/login/totp, donde
        # nuestro controller (controllers/home.py) le hace darla de alta con
        # QR antes de dejarle entrar. No hay fallback por email ni forma de
        # saltarse el paso.
        r = super()._mfa_type()
        return r or 'totp'

    def _should_alert_new_device(self):
        # auth_totp considera "nuevo" cualquier login sin dispositivo de
        # confianza, y ya no existen (models/auth_totp_device.py): sin esto
        # auth_signup mandaría un email de "nueva conexión" en cada login.
        return False

    @check_identity
    def action_totp_disable(self):
        # La 2FA es obligatoria (ver _mfa_type): un usuario no puede
        # desactivarse la suya propia, solo Administración/IT puede hacerlo
        # (p.ej. para recuperar el acceso si ha perdido el móvil).
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_(
                "No puedes desactivar tú mismo la autenticación en dos pasos (2FA). "
                "Es obligatoria para todos los usuarios. Si has perdido el acceso a tu "
                "aplicación de autenticación, contacta con IT."
            ))
        return super().action_totp_disable()
