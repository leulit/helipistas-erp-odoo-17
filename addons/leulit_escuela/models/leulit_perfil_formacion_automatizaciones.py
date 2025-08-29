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

class leulit_perfil_formacion(models.Model):
    _name = 'leulit.perfil_formacion'
    _inherit = 'leulit.perfil_formacion'


    def check_cursos_acciones(self):
        items = self.search([('inactivo','=',False)])
        email_values = {}
        for item in items:
            if item.alumno.name not in email_values:
                email_values[item.alumno.name] = {'cursos': [], 'acciones': []}
            for curso in item.cursos:
                if curso.next_done_date:
                    if curso.next_done_date < fields.Datetime.now().date() + relativedelta(months=3):
                        if curso.descripcion not in email_values[item.alumno.name]['cursos']:
                            email_values[item.alumno.name]['cursos'].append(curso.descripcion)
            for accion in item.acciones_new:
                if accion.next_done_date:
                    if accion.next_done_date < fields.Datetime.now().date() + relativedelta(months=3):
                        if accion.accion.name not in email_values[item.alumno.name]['acciones']:
                            email_values[item.alumno.name]['acciones'].append(accion.accion.name)
        
        template = self.env.ref('leulit_escuela.email_template_check_pf', raise_if_not_found=False)
        if template:
            email_context = {
                'email_values': email_values,
            }
            template.with_context(email_context).send_mail(self.env.user.id, force_send=True)

    def check_perfiles_caducados_hoy(self):
        items = self.search([('inactivo','=',False)])
        email_values = {}
        data = False
        for item in items:
            if item.name not in email_values:
                email_values[item.name] = {'cursos': [], 'acciones': []}
            for curso in item.cursos:
                if curso.next_done_date:
                    if curso.next_done_date == fields.Datetime.now().date():
                        data = True
                        if curso.descripcion not in email_values[item.name]['cursos']:
                            email_values[item.name]['cursos'].append(curso.descripcion)
            for accion in item.acciones_new:
                if accion.next_done_date:
                    if accion.next_done_date == fields.Datetime.now().date():
                        data = True
                        if accion.accion.name not in email_values[item.name]['acciones']:
                            email_values[item.name]['acciones'].append(accion.accion.name)
        
        template = self.env.ref('leulit_escuela.email_template_check_pf_hoy', raise_if_not_found=False)
        if template and data:
            email_context = {
                'email_values': email_values,
            }
            template.with_context(email_context).send_mail(self.env.user.id, force_send=True)