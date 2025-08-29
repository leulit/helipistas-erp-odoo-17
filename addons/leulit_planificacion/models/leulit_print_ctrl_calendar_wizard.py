# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_print_ctrl_calendar_wizard(models.Model):
    _name           = 'leulit.print_ctrl_calendar_wizard'
    _description    = 'leulit_print_ctrl_calendar_wizard'



    def imprimir(self):
        data = self._get_data_to_print_control_planificacion()
        return self.env.ref('leulit_planificacion.leulit_20220118_1037_report').report_action(self,data=data)
        

    def _get_data_to_print_control_planificacion(self):
        data = {}
        dias = []
        resta_fecha = self.to_date - self.from_date
        users = self.env['res.users'].search([],order='id asc')
        for i in range(resta_fecha.days+1):
            day = self.from_date + timedelta(days=i)
            eventos = self.env['calendar.event'].search([],order='start asc')
            eventos_fecha = []
            for evento in eventos:
                if day == evento.start.date():
                    eventos_fecha.append(evento)
            horas_realizadas = self.env['account.analytic.line'].search([('date','=',day)])
            datos_users = []
            for user in users:
                datos_eventos = []
                datos_tareas = []
                for evento in eventos_fecha:
                    for resource_field in evento.resource_fields:
                        if resource_field.resource.user.id == user.id:
                            eventos_planificados = {
                                'asunto' : evento.name,
                                'start_evento' : evento.start.strftime("%H:%M"),
                                'stop_evento' : evento.stop.strftime("%H:%M")
                            }
                            datos_eventos.append(eventos_planificados)
                for hora_realizada in horas_realizadas:
                    if hora_realizada.employee_id.user_id.id == user.id:
                        tiempo_imputado = {
                            'codigo' : hora_realizada.task_id.code,
                            'nombre_tarea' : hora_realizada.task_id.name,
                            'nombre' : hora_realizada.name,
                            'duracion' : utilitylib.leulit_float_time_to_str(hora_realizada.unit_amount)
                        }
                        datos_tareas.append(tiempo_imputado)
                if len(datos_tareas) > 0 or len(datos_eventos) > 0:
                    usuario = {
                        'nombre' : user.name,
                        'tareas' : datos_tareas,
                        'eventos' : datos_eventos
                    }
                    datos_users.append(usuario)
                    
            if len(datos_users) > 0:
                dia = {
                    'fecha' : day,
                    'users' : datos_users,
                }
                dias.append(dia)
        data = {
            'fechas' : dias
        }

        return data

    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')
    
