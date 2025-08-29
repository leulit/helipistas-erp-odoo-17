# -*- encoding: utf-8 -*-

from itertools import chain
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
import pytz
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp
import threading
from datetime import datetime, date, timedelta

from . import actividad_aerea_planificada

import logging
_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _get_float_time_start(self, fecha):
        if fecha:
            time_string = fecha.strftime("%H:%M")
            fields = time_string.split(":")
            hours = fields[0] if len(fields) > 0 else 0.0
            minutes = fields[1] if len(fields) > 1 else 0.0
            seconds = fields[2] if len(fields) > 2 else 0.0
            return float(hours) + (float(minutes) / 60.0) + (float(seconds) / pow(60.0, 2))
        return 0.0

    def _is_actividad_aerea(self):
        if self.type_event.is_vuelo:
            return True
        return False

    def _get_tipo_evento(self):
        if self.type_event.tipo_actividad == 'FI':
            return 'Formación Interna'
        else:
            return self.type_event.tipo_actividad

    def upd_datos_actividad(self):
        _logger.error("upd_datos_actividad ")
        threaded_calculation = threading.Thread(target=self.run_upd_datos_actividad, args=([]))
        _logger.error("upd_datos_actividad start thread")
        threaded_calculation.start()
        return {}

    def run_upd_datos_actividad(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            o_itemIaa = self.env['leulit.item_actividad_aerea'].with_context(context).search([('prevista','=',True)])
            o_itemIaa.with_context(context).unlink()
            new_cr.commit()
            o_aa = self.env['leulit.actividad_aerea'].with_context(context).search([('prevista','=',True)])
            o_aa.with_context(context).unlink()
            new_cr.commit()
            for parte in self.sudo().search([('start','>',datetime.now().strftime("%Y-%m-%d"))], order="start ASC"):
                parte.with_context(context).updDataPlanActividadAerea()
            new_cr.commit()
            new_cr.close()
            _logger.error("run_upd_datos_actividad fin")


    @api.model
    def initChainActividadAerea(self):
        chain1 = actividad_aerea_planificada.ItemActividadAreaHandler()
        chain2 = actividad_aerea_planificada.ActividadAereaPreVueloHandler()
        chain3 = actividad_aerea_planificada.CoeficienteMayoracionHandler()
        chain4 = actividad_aerea_planificada.CalcularActividadAerea()
        chain5 = actividad_aerea_planificada.CheckDescanso()
        chain6 = actividad_aerea_planificada.DiasTrabajadosMesHandler()
        chain7 = actividad_aerea_planificada.ItemActividadAreaValidFlightTimeHandler()
        
        chain1.set_next(chain2).set_next(chain3).set_next(chain4).set_next(chain5).set_next(chain6).set_next(chain7)
        return chain1

    def getDateTimeUTC(self):
        try:
            madrid_tz = pytz.timezone("Etc/GMT+2")
            mtz = madrid_tz.localize(datetime(self.start.year, self.start.month, self.start.day, self.start.hour, self.start.minute))
            dt_utc = mtz.astimezone(pytz.timezone('UTC'))
            return dt_utc.replace(tzinfo=None)
        except Exception as e:
            _logger.error("_date_end_utc %r",e)
            return None

    def updDataPlanActividadAerea(self):
        if not self.allday and self._is_actividad_aerea():
            for recurso in self.resource_fields:
                work_hours = recurso.work_hours
                if recurso.rol in ['5','2','6','7'] and work_hours > 0:
                    date_time = self.getDateTimeUTC()
                    handlerAA = self.initChainActividadAerea()
                    request = actividad_aerea_planificada.ActividadAereaPlanificadaChainRequest()
                    request.env = self.env
                    request.fecha = date_time.date()
                    request.inicio = self._get_float_time_start(date_time)
                    request.partner = recurso.resource.partner.id
                    request.horallegada = request.inicio + work_hours
                    request.tiempo = work_hours
                    request.idmodelo = self.id
                    request.prevista = True
                    request.modelo = 'calendar.event'
                    request.descripcion = self.name
                    request.tipo_actividad = self._get_tipo_evento()
                    request.escuela = True if self.type_event.tipo_actividad in ['FI','ATO'] else False
                    request.ato = True if self.type_event.tipo_actividad == 'ATO' else False
                    if recurso.rol == '5':
                        request.rol = "piloto_supervisor"
                        handlerAA.handle(request)
                    if recurso.rol == '2':
                        request.rol = "piloto"
                        handlerAA.handle(request)
                    if recurso.rol == '6':
                        request.rol = "profesor"
                        handlerAA.handle(request)
                    if recurso.rol == '7':
                        request.rol = "piloto"
                        handlerAA.handle(request)