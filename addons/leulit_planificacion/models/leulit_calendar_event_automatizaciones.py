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


class leulit_calendar_event(models.Model):
    _name = 'calendar.event'
    _inherit = 'calendar.event'


    @api.depends('recurrence_id')
    def _compute_recurrence_info(self):
        for event in self:
            if event.recurrence_id:
                event.first_event_date = event.recurrence_id.dtstart.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Europe/Madrid')).replace(tzinfo=None)
                event.last_event_date = event.recurrence_id.dtstop.replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('Europe/Madrid')).replace(tzinfo=None)
            else:
                event.first_event_date = event.start
                event.last_event_date = event.stop


    first_event_date = fields.Datetime(compute=_compute_recurrence_info, string='Primer Evento', store=False)
    last_event_date = fields.Datetime(compute=_compute_recurrence_info, string='Último Evento', store=False)
    email_abrir_permisos = fields.Boolean(string='')
    email_cerrar_permisos = fields.Boolean(string='')


    def open_permisos(self):
        fecha_end = fields.Datetime.now() + timedelta(days=30)
        fecha_start = fields.Datetime.now() + timedelta(days=15)
        fecha_hoy = fields.Datetime.now()
        fecha_7_dias_atras = fields.Datetime.now() - timedelta(days=7)
        tipos_evento = self.env['leulit.tipo_planificacion'].search([('tipo_actividad','in',['AOC','SPO'])])
        template = self.env.ref('leulit_planificacion.email_template_open_permission_event', raise_if_not_found=False)
        if template:
            # _logger.error('template')
            for item in self.search([('cancelado','=',False),('start', '>=', fecha_start),('start', '<=', fecha_end),('type_event','in',tipos_evento.ids)]):
                # _logger.error('item  --> %r',item)
                if item.recurrence_id:
                    if item.recurrence_id.base_event_id.id == item.id:
                        template.send_mail(item.id, force_send=True)
                        item.email_abrir_permisos = True
                else:
                    template.send_mail(item.id, force_send=True)
                    item.email_abrir_permisos = True
            for item in self.search([('cancelado','=',False),('create_date', '>=', fecha_7_dias_atras),('create_date', '<=', fecha_hoy),('start', '>=', fecha_hoy),('start', '<=', fecha_start),('type_event','in',tipos_evento.ids)]):
                # _logger.error('item  --> %r',item)
                if item.recurrence_id:
                    if item.recurrence_id.base_event_id.id == item.id:
                        template.send_mail(item.id, force_send=True)
                        item.email_abrir_permisos = True
                else:
                    template.send_mail(item.id, force_send=True)
                    item.email_abrir_permisos = True


    def close_permisos(self):
        fecha_start = fields.Datetime.now() - timedelta(days=7)
        tipos_evento = self.env['leulit.tipo_planificacion'].search([('tipo_actividad','in',['SPO'])])
        template = self.env.ref('leulit_planificacion.email_template_close_permission_event', raise_if_not_found=False)
        if template:
            # _logger.error('template')
            for item in self.search([('cancelado','=',False),('start', '>=', fecha_start),('start', '<=', fields.Datetime.now()),('type_event','in',tipos_evento.ids)]):
                # _logger.error('item  --> %r',item)
                if item.recurrence_id:
                    if item.recurrence_id.base_event_id.id == item.id:
                        template.send_mail(item.id, force_send=True)
                        item.email_cerrar_permisos = True
                else:
                    template.send_mail(item.id, force_send=True)
                    item.email_cerrar_permisos = True


    def potencial_aeronaves(self):
        fecha_end = fields.Datetime.now() + relativedelta(months=1)
        fecha_hoy = fields.Datetime.now()
        tipos_evento = self.env['leulit.tipo_planificacion'].search([('name','in',['Taller'])])
        template = self.env.ref('leulit_planificacion.email_template_potencial_aeronaves_event', raise_if_not_found=False)
        email_values = {}
        if template:
            # _logger.error('template')
            for recurso in self.env['leulit.resource'].search([('type','=','maquina'),('aeronave','!=',False)]):
                if recurso.aeronave.ctrloperaciones:
                    email_values[recurso.name] = []
                    if recurso.aeronave.statemachine == 'En taller':
                        work_hours = 50
                    else:
                        work_hours = recurso.aeronave.horas_remanente
                    email_values[recurso.name].append({
                        'fecha': fecha_hoy.date(),
                        'horas': round(work_hours, 2),
                        'taller': ''
                    })
                    for item in self.env['leulit.event_resource'].search([('cancelado','=',False),('fecha_ini', '>=', fecha_hoy),('fecha_ini', '<=', fecha_end),('resource','=',recurso.id)], order='fecha_ini asc'):
                        # _logger.error('item  --> %r',item)
                        if item.type_event.id in tipos_evento.ids:
                            date_start_event = item.event.start
                            email_values[recurso.name].append({
                                'fecha': date_start_event.date(),
                                'horas': round(work_hours, 2),
                                'taller': 'Inicio Taller'
                            })
                            date_stop_event = item.event.stop
                            work_hours = 50
                            email_values[recurso.name].append({
                                'fecha': date_stop_event.date(),
                                'horas': round(work_hours, 2),
                                'taller': 'Fin Taller'
                            })
                        else:
                            work_hours -= item.work_hours
                    email_values[recurso.name].append({
                        'fecha': fecha_end.date(),
                        'horas': round(work_hours, 2),
                        'taller': ''
                    })

        email_context = {
            'email_values': email_values,
        }
        template.with_context(email_context).send_mail(self.env.user.id, force_send=True)


    def check_equipamientos(self):
        fecha_start = (fields.Datetime.now() + timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_end = (fields.Datetime.now() + timedelta(days=3)).replace(hour=23, minute=59, second=59, microsecond=999999)
        tipos_evento = self.env['leulit.tipo_planificacion'].search([('tipo_actividad','in',['SPO','AOC'])])
        template = self.env.ref('leulit_planificacion.email_template_check_equipamientos', raise_if_not_found=False)
        if template:
            for item in self.search([('cancelado','=',False), ('start', '>=', fecha_start), ('start', '<=', fecha_end), ('type_event','in',tipos_evento.ids)]):
                if item.equipamientos_ids:
                    partners_with_email = [partner for partner in item.partner_ids if partner.email and partner.user_ids]
                    for partner in partners_with_email:
                        employee_ids = self.env['hr.employee'].search([('user_id', 'in', partner.user_ids.ids)])
                        if employee_ids:
                            email_context = {
                                'mail_to': partner.email,
                            }
                            if item.recurrence_id:
                                if item.recurrence_id.base_event_id.id == item.id:
                                    template.with_context(email_context).send_mail(item.id, force_send=True)
                            else:
                                template.with_context(email_context).send_mail(item.id, force_send=True)


    def notify_customers(self):
        fecha_end = fields.Datetime.now() + timedelta(days=30)
        fecha_start = fields.Datetime.now() + timedelta(days=15)
        tipos_evento = self.env['leulit.tipo_planificacion'].search([('tipo_actividad','in',['SPO'])])
        template = self.env.ref('leulit_planificacion.email_template_notify_customer_event', raise_if_not_found=False)
        if template:
            # _logger.error('template')
            for item in self.search([('cancelado','=',False),('start', '>=', fecha_start),('start', '<=', fecha_end),('type_event','in',tipos_evento.ids)]):
                # _logger.error('item  --> %r',item)
                if item.recurrence_id:
                    if item.recurrence_id.base_event_id.id == item.id:
                        template.send_mail(item.id, force_send=True)
                else:
                    template.send_mail(item.id, force_send=True)

    
    def close_sale_order(self):
        fecha_start = (fields.Datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_end = (fields.Datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        tipos_evento = self.env['leulit.tipo_planificacion'].search([('tipo_actividad','in',['SPO','AOC'])])
        template = self.env.ref('leulit_planificacion.email_template_close_sale_order_event', raise_if_not_found=False)
        if template:
            # _logger.error('template')
            for item in self.search([('cancelado','=',False), ('start', '>=', fecha_start), ('start', '<=', fecha_end), ('type_event','in',tipos_evento.ids)]):
                # _logger.error('item  --> %r',item)
                if item.sale_order_id:
                    more_events = self.search([('cancelado','=',False), ('start', '>', fecha_end),('sale_order_id','=',item.sale_order_id.id)])
                    if len(more_events) == 0:
                        template.send_mail(item.id, force_send=True)


    def notify_formacion_interna(self):
        fecha_end = fields.Datetime.now() + relativedelta(months=1)
        fecha_start = fields.Datetime.now()
        tipos_evento = self.env['leulit.tipo_planificacion'].search([('tipo_actividad','in',['FI'])])
        template = self.env.ref('leulit_planificacion.email_template_notify_formacion_interna', raise_if_not_found=False)
        email_values = {}
        if template:
            # _logger.error('template')
            for item in self.search([('cancelado','=',False), ('start', '>=', fecha_start), ('start', '<=', fecha_end), ('type_event','in',tipos_evento.ids)]):
                participantes = ', '.join([partner.name for partner in item.partner_ids])
                email_values[item.name] = {
                    'fecha': item.start.astimezone(pytz.timezone("Europe/Madrid")),
                    'participantes': participantes
                }
            email_context = {
                'email_values': email_values,
                'values_flag': True if len(email_values) > 0 else False,
            }
            template.with_context(email_context).send_mail(self.env.user.id, force_send=True)