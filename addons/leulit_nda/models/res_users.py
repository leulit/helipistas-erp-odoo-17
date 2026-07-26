# -*- encoding: utf-8 -*-
import base64
import logging
import random
from datetime import timedelta

from odoo import models, fields, _, SUPERUSER_ID
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

NDA_CODIGO_TTL_MINUTOS = 15
NDA_CODIGO_MAX_INTENTOS = 5


class ResUsers(models.Model):
    _inherit = "res.users"

    nda_firmado = fields.Boolean(string="NDA firmado", default=False, copy=False)
    nda_fecha_firma = fields.Datetime(string="Fecha de firma del NDA", copy=False)
    nda_codigo = fields.Char(string="Código NDA pendiente", copy=False)
    nda_codigo_expiracion = fields.Datetime(string="Expiración código NDA", copy=False)
    nda_codigo_intentos = fields.Integer(string="Intentos código NDA", default=0, copy=False)

    def _nda_debe_firmar(self):
        """Indica si el usuario tiene bloqueado el acceso al backend hasta firmar el NDA."""
        self.ensure_one()
        if self.id == SUPERUSER_ID or not self._is_internal() or self.nda_firmado:
            return False
        icp = self.env["ir.config_parameter"].sudo()
        return icp.get_param("leulit_nda.enforce", "True") == "True"

    def action_nda_enviar_codigo(self):
        """Genera un código de 6 cifras y lo envía por email al usuario."""
        self.ensure_one()
        if not self.email:
            raise UserError(_("Tu usuario no tiene un email configurado. Por favor contacta con el administrador."))

        self.sudo().write({
            "nda_codigo": "%06d" % random.randint(0, 999999),
            "nda_codigo_expiracion": fields.Datetime.now() + timedelta(minutes=NDA_CODIGO_TTL_MINUTOS),
            "nda_codigo_intentos": 0,
        })

        template = self.env.ref("leulit_nda.mail_template_nda_codigo")
        template.sudo().send_mail(
            self.id,
            force_send=True,
            email_values={
                "email_to": self.email,
                "recipient_ids": [],
            },
        )
        _logger.info("Código NDA enviado al usuario %s (%s)", self.login, self.email)

    def action_nda_verificar_codigo(self, codigo):
        """Valida el código introducido y, si es correcto, marca el NDA como firmado."""
        self.ensure_one()
        user = self.sudo()
        error_msg = _("El código introducido no es válido. Vuelve a intentarlo o contacta con el administrador del sistema.")

        if (
            not user.nda_codigo
            or not user.nda_codigo_expiracion
            or user.nda_codigo_expiracion < fields.Datetime.now()
            or user.nda_codigo_intentos >= NDA_CODIGO_MAX_INTENTOS
        ):
            raise UserError(error_msg)

        if (codigo or "").strip() != user.nda_codigo:
            user.nda_codigo_intentos += 1
            raise UserError(error_msg)

        user.write({
            "nda_firmado": True,
            "nda_fecha_firma": fields.Datetime.now(),
            "nda_codigo": False,
            "nda_codigo_expiracion": False,
            "nda_codigo_intentos": 0,
        })
        user._nda_generar_y_enviar_pdf()
        _logger.info("NDA firmado por el usuario %s", user.login)

    def _nda_generar_y_enviar_pdf(self):
        """Genera el PDF del acuerdo firmado y lo envía por email como adjunto."""
        self.ensure_one()
        user = self.sudo()

        report = self.env.ref("leulit_nda.leulit_nda_report")
        pdf_content, dummy = self.env["ir.actions.report"].sudo()._render_qweb_pdf(report, user.ids)
        attachment = self.env["ir.attachment"].sudo().create({
            "name": _("Acuerdo NDA firmado - %s.pdf") % user.name,
            "type": "binary",
            "datas": base64.b64encode(pdf_content),
            "res_model": "res.users",
            "res_id": user.id,
        })

        template = self.env.ref("leulit_nda.mail_template_nda_firmado")
        template.sudo().send_mail(
            user.id,
            force_send=True,
            email_values={
                "email_to": user.email,
                "recipient_ids": [],
                "attachment_ids": [(6, 0, [attachment.id])],
            },
        )
