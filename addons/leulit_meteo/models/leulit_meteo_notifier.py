# -*- coding: utf-8 -*-
"""Utilidad centralizada de notificación de errores para leulit_meteo.

Proporciona la función ``meteo_notify_error`` que cualquier parte del módulo
puede llamar cuando tiene acceso a ``env``.  Lee el destinatario de
``leulit_meteo.email_errores`` (ir.config_parameter).  Si está vacío no hace
nada (falla silenciosa con log).
"""
import logging
from odoo import fields

_logger = logging.getLogger(__name__)

PARAM_EMAIL_ERRORES = 'leulit_meteo.email_errores'


def _esc(s):
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def meteo_notify_error(env, componente, error, traceback_str=None, contexto=None):
    """Envía email de error al destinatario configurado en Parámetros → Meteorología.

    :param env:           Entorno Odoo (con permisos sudo si es necesario).
    :param componente:    Nombre del componente que falló (str).
    :param error:         Excepción o mensaje de error (Exception | str).
    :param traceback_str: Traceback completo como string (traceback.format_exc()).
    :param contexto:      Dict con pares clave-valor de contexto adicional.
    """
    email_to = env['ir.config_parameter'].sudo().get_param(PARAM_EMAIL_ERRORES, '')
    if not email_to:
        _logger.debug(
            "meteo_notify_error: email_errores no configurado; error en '%s' no notificado.",
            componente)
        return

    ahora = fields.Datetime.now().strftime('%d/%m/%Y %H:%M UTC')
    error_type = type(error).__name__ if isinstance(error, Exception) else 'Error'
    error_msg = str(error)

    # --- Contexto adicional ---
    contexto_html = ''
    if contexto:
        filas = ''.join(
            f'<tr>'
            f'<td style="padding:4px 10px;border:1px solid #ddd;font-weight:bold;'
            f'background:#f9f9f9;white-space:nowrap;">{_esc(k)}</td>'
            f'<td style="padding:4px 10px;border:1px solid #ddd;">{_esc(v)}</td>'
            f'</tr>'
            for k, v in contexto.items()
        )
        contexto_html = (
            '<p style="margin:16px 0 4px;font-weight:bold;">Contexto:</p>'
            '<table style="border-collapse:collapse;width:100%;margin-bottom:12px;">'
            + filas + '</table>'
        )

    # --- Traceback ---
    traceback_html = ''
    if traceback_str:
        traceback_html = (
            '<p style="margin:16px 0 4px;font-weight:bold;">Traceback completo:</p>'
            '<pre style="background:#f8f8f8;border:1px solid #ddd;padding:12px;'
            'font-family:monospace;font-size:11px;overflow-x:auto;'
            'white-space:pre-wrap;word-break:break-all;margin:0;">'
            + _esc(traceback_str) + '</pre>'
        )

    body = f"""
<div style="font-family:sans-serif;max-width:720px;">
  <div style="background:#b00;color:#fff;padding:10px 18px;border-radius:4px 4px 0 0;">
    <strong>Error en m&#243;dulo de Meteorolog&#237;a</strong>
  </div>
  <div style="border:1px solid #ddd;border-top:none;padding:16px 18px;background:#fff;">
    <table style="border-collapse:collapse;width:100%;margin-bottom:8px;">
      <tr>
        <td style="padding:5px 10px;border:1px solid #ddd;font-weight:bold;
                   background:#f9f9f9;width:160px;white-space:nowrap;">Fecha/Hora (UTC)</td>
        <td style="padding:5px 10px;border:1px solid #ddd;">{ahora}</td>
      </tr>
      <tr>
        <td style="padding:5px 10px;border:1px solid #ddd;font-weight:bold;background:#f9f9f9;">
          Componente</td>
        <td style="padding:5px 10px;border:1px solid #ddd;">{_esc(componente)}</td>
      </tr>
      <tr>
        <td style="padding:5px 10px;border:1px solid #ddd;font-weight:bold;background:#f9f9f9;">
          Tipo de error</td>
        <td style="padding:5px 10px;border:1px solid #ddd;color:#b00;font-weight:bold;">
          {_esc(error_type)}</td>
      </tr>
      <tr>
        <td style="padding:5px 10px;border:1px solid #ddd;font-weight:bold;background:#f9f9f9;">
          Mensaje</td>
        <td style="padding:5px 10px;border:1px solid #ddd;color:#b00;">{_esc(error_msg)}</td>
      </tr>
    </table>
    {contexto_html}
    {traceback_html}
  </div>
  <div style="padding:8px 18px;background:#f5f5f5;border:1px solid #ddd;border-top:none;
              font-size:11px;color:#888;border-radius:0 0 4px 4px;">
    Mensaje autom&#225;tico del m&#243;dulo de Meteorolog&#237;a (leulit_meteo).
  </div>
</div>"""

    subject = f'[Meteorología] Error en {componente}: {error_type}'
    try:
        env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body,
            'email_to': email_to,
            'auto_delete': True,
        }).send()
        _logger.info(
            "meteo_notify_error: notificacion enviada a %s [%s]",
            email_to, componente)
    except Exception as exc:
        _logger.error("meteo_notify_error: fallo al enviar email: %s", exc)
