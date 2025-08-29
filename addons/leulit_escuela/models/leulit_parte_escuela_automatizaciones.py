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

class leulit_parte_escuela(models.Model):
    _name = 'leulit.parte_escuela'
    _inherit = 'leulit.parte_escuela'


    def check_partes_pendientes(self):
        fecha_end = fields.Datetime.now()
        template = self.env.ref('leulit_escuela.email_template_check_partes_escuela_pendientes', raise_if_not_found=False)
        if template:
            # _logger.error('template --> %r', template)
            for profesor in self.env['leulit.profesor'].search([]):
                # _logger.error('profesor --> %r', profesor)
                email_values = {}
                if profesor.employee.active:
                    partes_pendientes = self.search([('estado', '=', 'pendiente'),('fecha', '<', fecha_end),('profesor', '=', profesor.id)])
                    if partes_pendientes:
                        email_values[profesor.name] = [{'name': parte.name, 'id': parte.id, 'fecha': parte.fecha} for parte in partes_pendientes]
                        email_context = {
                            'mail_to': profesor.email,
                            'email_values': email_values,
                        }
                        template.with_context(email_context).send_mail(self.env.user.id, force_send=True)


    def check_partes_sin_verificar(self):
        fecha_hoy = fields.Datetime.now()
        template = self.env.ref('leulit_escuela.email_template_check_partes_escuela_sin_verificar', raise_if_not_found=False)
        if template:
            # _logger.error('template --> %r', template)
            for alumno in self.env['leulit.alumno'].search([]):
                # _logger.error('alumno --> %r', alumno)
                email_values = {}
                lineas_sin_verificar = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('estado', '=', 'cerrado'),('fecha', '<', fecha_hoy),('alumno', '=', alumno.id),('verificado', '=', False)])
                partes_dict = {}
                for linea in lineas_sin_verificar:
                    parte_id = linea.rel_parte_escuela.id
                    if parte_id not in partes_dict:
                        partes_dict[parte_id] = {
                            'name': linea.rel_parte_escuela.name,
                            'id': parte_id,
                            'fecha': linea.fecha,
                        }
                
                if partes_dict:
                    email_values[alumno.name] = list(partes_dict.values())
                    email_context = {
                        'mail_to': alumno.email,
                        'email_values': email_values,
                    }
                    template.with_context(email_context).send_mail(self.env.user.id, force_send=True)