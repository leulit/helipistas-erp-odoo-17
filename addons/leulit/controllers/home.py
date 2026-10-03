# -*- coding: utf-8 -*-
import base64
import functools
import io
import logging
import os
import re

import qrcode
import werkzeug.urls

from odoo import http, _
from odoo.exceptions import AccessDenied
from odoo.http import request

import odoo.addons.auth_totp.controllers.home as auth_totp_home
from odoo.addons.auth_totp.models.totp import ALGORITHM, DIGITS, TIMESTEP, TOTP, TOTP_SECRET_SIZE

_logger = logging.getLogger(__name__)

compress = functools.partial(re.sub, r'\s', '')

# Guarda el secreto TOTP generado para el alta obligatoria mientras el
# usuario todavía está en la fase de pre-login (pre_uid, sin uid). Vive solo
# en la sesión del navegador que está iniciando sesión: si no termina el
# alta, no queda nada escrito en el usuario.
SETUP_SECRET_SESSION_KEY = 'leulit_totp_setup_secret'


class Home(auth_totp_home.Home):

    @http.route()
    def web_totp(self, redirect=None, **kwargs):
        # Sin "no volver a preguntar en este dispositivo": aunque alguien
        # mande el parámetro a mano, no se crea dispositivo de confianza.
        kwargs.pop('remember', None)
        # Si ya hay sesión completa, o no hay pre-login en curso, no hay nada
        # que decidir: delega en el comportamiento estándar (auth_totp).
        if request.session.uid or not request.session.pre_uid:
            return super().web_totp(redirect=redirect, **kwargs)

        user = request.env['res.users'].sudo().browse(request.session.pre_uid)
        if user.totp_enabled:
            # Ya tiene la app configurada: el formulario estándar de
            # "introduce el código de 6 dígitos" es suficiente.
            return super().web_totp(redirect=redirect, **kwargs)

        # Primer login sin 2FA configurada todavía: en vez de dejarle pasar
        # (comportamiento de base) le obligamos a darla de alta aquí mismo,
        # con QR, antes de completar el login. No hay forma de omitir este
        # paso ni fallback alternativo (p.ej. por email).
        return self._totp_setup(user, redirect=redirect, **kwargs)

    def _totp_setup(self, user, redirect=None, **kwargs):
        error = None
        secret = request.session.get(SETUP_SECRET_SESSION_KEY)
        if not secret:
            secret = base64.b32encode(os.urandom(TOTP_SECRET_SIZE // 8)).decode()
            request.session[SETUP_SECRET_SESSION_KEY] = secret

        if request.httprequest.method == 'POST' and kwargs.get('totp_token'):
            try:
                code = int(compress(kwargs['totp_token']))
            except ValueError:
                error = _("Invalid authentication code format.")
            else:
                try:
                    with user._assert_can_auth(user=user.id):
                        match = TOTP(base64.b32decode(secret)).match(code)
                except AccessDenied as e:
                    error = str(e)
                    match = None
                if error is None:
                    if match is None:
                        _logger.info("2FA setup: REJECT CODE for %s %r", user, user.login)
                        error = _("Verification failed, please double-check the 6-digit code")
                    else:
                        user.totp_secret = compress(secret).upper()
                        request.session.pop(SETUP_SECRET_SESSION_KEY, None)
                        _logger.info("2FA setup: SUCCESS for %s %r", user, user.login)

                        # finalize() calcula el session_token leyendo
                        # totp_secret (auth_totp._get_session_token_fields);
                        # hay que vaciar antes la escritura pendiente del ORM
                        # o calcularía el token con el secreto todavía vacío
                        # (mismo patrón que auth_totp._totp_try_setting).
                        request.env.flush_all()
                        request.session.finalize(request.env)
                        request.update_env(user=request.session.uid)
                        request.update_context(**request.session.context)
                        response = request.redirect(self._login_redirect(request.session.uid, redirect=redirect))
                        request.session.touch()
                        return response

        return request.render('leulit.auth_totp_setup_form', {
            'user': user,
            'secret_groups': ' '.join(map(''.join, zip(*[iter(compress(secret).upper())] * 4))),
            'qrcode': self._totp_setup_qrcode(user, secret),
            'error': error,
            'redirect': redirect,
        })

    def _totp_setup_qrcode(self, user, secret):
        issuer = request.httprequest.host.split(':', 1)[0]
        url = werkzeug.urls.url_unparse((
            'otpauth', 'totp',
            werkzeug.urls.url_quote(f'{issuer}:{user.login}', safe=':'),
            werkzeug.urls.url_encode({
                'secret': compress(secret),
                'issuer': issuer,
                'algorithm': ALGORITHM.upper(),
                'digits': DIGITS,
                'period': TIMESTEP,
            }), ''
        ))
        data = io.BytesIO()
        qrcode.make(url.encode(), box_size=4).save(data, optimize=True, format='PNG')
        return base64.b64encode(data.getvalue()).decode()
