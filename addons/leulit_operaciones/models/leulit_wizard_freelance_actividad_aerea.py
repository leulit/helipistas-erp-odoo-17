# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
import random
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class leulitWizardFreelanceActividadAerea(models.TransientModel):
    _name           = "leulit.wizard_freelance_actividad_aerea"
    _description    = "leulit_wizard_freelance_actividad_aerea"


    def send_code_mail(self):
        """Sends the code via email."""
        self.ensure_one()
        
        # Generar el código antes de enviar el email
        self.code_sent = random.randint(100000, 999999)
        
        # Verificar que el usuario tenga email
        if not self.env.user.email:
            raise UserError(_("Tu usuario no tiene un email configurado. Por favor contacta al administrador."))
        
        template = self.env.ref('leulit_operaciones.leulit_20250320_1123_template')
        if template:
            # Enviar el email forzando el destinatario al usuario actual
            template.send_mail(
                self.id, 
                force_send=True,
                email_values={
                    'email_to': self.env.user.email,
                    'recipient_ids': []  # Evitar que use recipient_ids del template
                }
            )
        else:
            raise UserError(_("Email template not found. Por favor contacta al administrador."))
        
        # Retornar una acción para mantener el popup abierto
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actividad Aerea Pilotos Freelance',
            'res_model': 'leulit.wizard_freelance_actividad_aerea',
            'view_mode': 'form',
            'view_id': self.env.ref('leulit_operaciones.leulit_20250320_1123_form').id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context,
        }

    def accept_certificate_actividad_aerea(self):
        """Accepts the certificate of the activity."""
        if self.code == self.code_sent:
            self.env['leulit.freelance_actividad_aerea'].create({
                'user': self.env.uid,
                'date': self.date,
                'text': self.text,
                'company': self.env.company.id,
            })
        else:
            raise UserError(_("El codigo entrado es incorrecto."))

    text = fields.Text(string="Texto")
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    code = fields.Integer(string="Código", default=0)
    code_sent = fields.Integer(string="Código enviado", default=0)