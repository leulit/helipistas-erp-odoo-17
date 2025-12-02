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

from . import actividad_aerea
from . import actividad_laboral

import logging
_logger = logging.getLogger(__name__)


class ParteVuelo(models.Model):
    _inherit = "leulit.vuelo"


    def upd_datos_actividad(self, fecha_origen, fecha_fin):
        _logger.error("upd_datos_actividad ")
        threaded_calculation = threading.Thread(target=self.run_upd_datos_actividad, args=([fecha_origen,fecha_fin]))
        _logger.error("upd_datos_actividad start thread")
        threaded_calculation.start()
        return {}

    def run_upd_datos_actividad(self, fecha_origen, fecha_fin):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            context = dict(self._context)

            aa_line_ids = env['account.analytic.line'].search([
                ('vuelo_no_hlp', '=', True),
                ('date_time', '>=', (datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d"))
            ])
            if fecha_origen and fecha_fin:
                aa_line_ids = env['account.analytic.line'].search([
                    ('vuelo_no_hlp', '=', True),
                    ('date_time', '>=', fecha_origen),
                    ('date_time', '<=', fecha_fin)
                ])
            for line in aa_line_ids:
                line.with_context(context).updDataActividadAerea()

            aa_no_introd = env['leulit.actividad_aerea_no_introducida'].search([])
            if aa_no_introd:
                for item in aa_no_introd:
                    for parte in env['leulit.vuelo'].search([
                        ('estado', '=', 'cerrado'),
                        ('fechavuelo', '=', item.fecha)
                    ], order="horasalida ASC"):
                        parte.with_context(context).updDataActividadAerea()
                    item.unlink()
                    new_cr.commit()

            domains = [
                [('estado', '=', 'cerrado'), ('fechavuelo', '>=', (datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d"))],
            ]
            if fecha_origen and fecha_fin:
                domains = [
                    [('estado', '=', 'cerrado'), ('fechavuelo', '>=', fecha_origen), ('fechavuelo', '<=', fecha_fin)]
                ]

            for domain in domains:
                for parte in env['leulit.vuelo'].search(domain, order="fechavuelo ASC, horasalida ASC"):
                    parte.with_context(context).updDataActividadAerea()
            new_cr.commit()
            _logger.error("run_upd_datos_actividad fin")


    @api.model
    def initChainActividadLaboral(self):
        chain1 = actividad_laboral.LaboralPreVueloHandler()
        chain2 = actividad_laboral.SolapamientoHandler()
        chain3 = actividad_laboral.ActividadBaseHandler()
        chain4 = actividad_laboral.ActividadBaseDiaHandler()
        chain1.set_next(chain2).set_next(chain3).set_next(chain4)
        return chain1

    @api.model
    def initChainActividadAerea(self):
        chain0 = actividad_aerea.DeleteData()
        chain1 = actividad_aerea.CheckOverlap()
        chain2 = actividad_aerea.DeleteItemsActividadAereaPrevistaPrevia()
        chain3 = actividad_aerea.ActividadAereaPreVueloHandler()
        chain5 = actividad_aerea.ItemActividadAreaHandler()
        chain4 = actividad_aerea.CoeficienteMayoracionHandler()
        chain6 = actividad_aerea.CalcularActividadAerea()
        chain7 = actividad_aerea.CheckDescanso()
        chain11 = actividad_aerea.DiasTrabajadosMesHandler()
        chain12 = actividad_aerea.ItemActividadAreaValidFlightTimeHandler()
        chain13 = actividad_aerea.ParteEscuelaHandler()

        chain1.set_next(chain2).set_next(chain5).set_next(chain3).set_next(chain4).set_next(chain13).set_next(chain6).set_next(chain7).set_next(chain11).set_next(chain12)
        return chain1


    def updDataActividadAerea(self):
        # CADENA PROCESAMIENTO ACTIVIDAD AEREA
        if self.estado == 'cerrado':
            handlerAA = self.initChainActividadAerea()
            request = actividad_aerea.ActividadAereaChainRequest()
            request.env = self.env
            request.fecha = self.fechavuelo
            request.inicio = self.horasalida

            request.horallegada = self.horallegada            
            request.tiempo = self.tiemposervicio
            request.airtime = self.airtime
            request.idmodelo = self.id
            request.prevista = False
            request.modelo = 'leulit.vuelo'
            request.descripcion = self.codigo
            request.tipo_actividad = self.tipo_actividad
            request.escuela = True if self.parte_escuela_id else False
            request.ato = True if self.parte_escuela_id and self.parte_escuela_id.isvueloato(self.id) else False
            request.env = self.env
            if self.piloto_id:
                request.partner = self.piloto_id.sudo().getPartnerId()
                request.rol = "piloto"
                handlerAA.handle(request)
            if self.alumno:
                request.partner = self.alumno.sudo().getPartnerId()
                request.rol = "alumno"
                handlerAA.handle(request)
            if self.operador:
                request.partner = self.operador.sudo().getPartnerId()
                request.rol = "operador"
                handlerAA.handle(request)
            if self.verificado:
                request.partner = self.verificado.sudo().getPartnerId()
                request.rol = "verificado"
                handlerAA.handle(request)


    def create_account_line(self, datos):
        try:
            context = dict(self.env.context)
            context.update({
                'not_check_overlap_account_analytic_line': False,
            })            
            idaal = self.env["account.analytic.line"].with_context(context).sudo().create( datos )

            sql = "UPDATE account_analytic_line SET date_time = TO_TIMESTAMP('{date_time}','YYYY-MM-DD HH24:MI') WHERE id = {id};".format(
                date_time= datos['date_time'].strftime("%Y-%m-%d %H:%M") ,
                id = idaal.id
            )
            self._cr.execute(sql)
            self._cr.commit()
            for item in self:
                if item.fechavuelo != datetime.now().date():
                    self.env['leulit.actividad_aerea_no_introducida'].create({'fecha': item.fechavuelo})
        except Exception as exc:
            import traceback
            import json
            strtraceback = traceback.format_exc()
            fecha = fields.Datetime.now()       
            self.env['leulit.error_import'].sudo().create({
                'tabla' : "account.analytic.line",
                'datos' : datos['name'],
                'comments' : "ERROR CREANDO TIMESHEET PARTE DE VUELO",
                'fecha' : fecha
            })    

            self.env.cr.rollback()  

    
    def updDataActividadLaboralByDay(self, vuelo, partner_id, employee_id):
        _logger.error('updDataActividadLaboralByDay {0} {1} {2}'.format(vuelo.fechavuelo, partner_id, employee_id))
        result = self.env['account.analytic.line'].search( [('idmodelo','=',vuelo.id),('modelo','=','leulit.vuelo'),('partner_id','=',partner_id)] )
        if not result:
            _logger.error('No existe la linea de tiempo de la actividad para el dia {0} y el vuelo {1}'.format(vuelo.fechavuelo, vuelo.id))
            idproject = self.env['ir.config_parameter'].sudo().get_param('leulit.flight_hours_project')
            tiemposervicio = (utilitylib.leulit_float_time_to_minutes(vuelo.tiemposervicio)+75)/60
            datetime = self.getDateTimeUTC(vuelo.fechavuelo, (utilitylib.leulit_float_time_to_minutes(vuelo.horasalida)-45)/60, vuelo.lugarsalida.tz)
            datos = {
                "date_time": datetime,
                "unit_amount": tiemposervicio,
                "date": vuelo.fechavuelo,
                "project_id": int(idproject),
                "name": vuelo.codigo,
                "ref": vuelo.codigo,
                "partner_id": partner_id,
                "employee_id": employee_id,
                "modelo" : 'leulit.vuelo',
                "idmodelo" : vuelo.id,
                "product_uom_id" : 4,
            }
            self.create_account_line(datos)
        result = self.env['account.analytic.line'].search( [('idmodelo','=',vuelo.id),('modelo','=','leulit.vuelo'),('partner_id','=',partner_id)] )
        _logger.error('{0} {1} {2}'.format(self.fechavuelo, self.horasalida, self.lugarsalida.tz))
        if result.date_time < self.getDateTimeUTC( self.fechavuelo, self.horasalida, self.lugarsalida.tz):
            if (utilitylib.leulit_float_time_to_minutes(vuelo.tiemposervicio) + 45)/60 != result.unit_amount and (utilitylib.leulit_float_time_to_minutes(vuelo.tiemposervicio) + 75)/60 == result.unit_amount:
                result.unit_amount = (utilitylib.leulit_float_time_to_minutes(result.unit_amount) - 30)/60
            return False
        else:
            return True


    def updDataActividadLaboralByEmployeeId(self, employee_id, partner_id):
        idproject = self.env['ir.config_parameter'].sudo().get_param('leulit.flight_hours_project')
        notLast = False
        for vuelo in self.search([('fechavuelo','=',self.fechavuelo),('id','!=',self.id),('estado','=','cerrado')],order="horasalida asc"):
            if vuelo.piloto_id.getPartnerId() == partner_id:
                result = self.updDataActividadLaboralByDay(vuelo, partner_id, employee_id)
                if result:
                    notLast = True
            if vuelo.operador.getPartnerId() == partner_id:
                result = self.updDataActividadLaboralByDay(vuelo, partner_id, employee_id)
                if result:
                    notLast = True
            if vuelo.piloto_supervisor_id.getPartnerId() == partner_id:
                result = self.updDataActividadLaboralByDay(vuelo, partner_id, employee_id)
                if result:
                    notLast = True
        if notLast:
            tiemposervicio = (utilitylib.leulit_float_time_to_minutes(self.tiemposervicio)+45)/60
        else:
            tiemposervicio = (utilitylib.leulit_float_time_to_minutes(self.tiemposervicio)+75)/60
        datetime = self.getDateTimeUTC(self.fechavuelo, (utilitylib.leulit_float_time_to_minutes(self.horasalida)-45)/60, self.lugarsalida.tz)
        datos = {
            "date_time": datetime,
            "unit_amount": tiemposervicio,
            "date": self.fechavuelo,
            "project_id": int(idproject),
            "name": self.codigo,
            "ref": self.codigo,
            "partner_id": partner_id,
            "employee_id": employee_id,
            "modelo" : "leulit.vuelo",
            "idmodelo" : self.id,
            "product_uom_id" : 4,
        }
        self.create_account_line(datos)


    def updDataActividadLaboral(self):
        for item in self:
            if item.estado == 'cerrado':
                item.write({'estado': 'cerrado'})
                

    @api.model
    def create(self, values):
        newRecord  = super().create(values)
        return newRecord


    def after_update_create_tiempo_imputado(self):
        if self.estado == 'cerrado':
            if ((self.sudo().piloto_id) and (self.sudo().piloto_id.employee)):
                result = self.env['account.analytic.line'].search( [('idmodelo','=',self.id),('modelo','=','leulit.vuelo'),('employee_id','=',self.sudo().piloto_id.employee.id)] )
                if not result:
                    self.updDataActividadLaboralByEmployeeId( self.sudo().piloto_id.employee.id, self.sudo().piloto_id.getPartnerId())
                    self.tiempo_imputado_piloto = True

            if ((self.sudo().operador) and (self.sudo().operador.employee)):
                result = self.env['account.analytic.line'].search( [('idmodelo','=',self.id),('modelo','=','leulit.vuelo'),('employee_id','=',self.sudo().operador.employee.id)] )
                if not result:
                    self.updDataActividadLaboralByEmployeeId( self.sudo().operador.employee.id, self.sudo().operador.getPartnerId())
                    self.tiempo_imputado_operador = True

            if ((self.sudo().piloto_supervisor_id) and (self.sudo().piloto_supervisor_id.employee)):
                result = self.env['account.analytic.line'].search( [('idmodelo','=',self.id),('modelo','=','leulit.vuelo'),('employee_id','=',self.sudo().piloto_supervisor_id.employee.id)] )
                if not result:
                    self.updDataActividadLaboralByEmployeeId( self.sudo().piloto_supervisor_id.employee.id, self.sudo().piloto_supervisor_id.getPartnerId())
                    self.tiempo_imputado_supervisor = True


    def wizardSetPrevuelo(self):
        self.tiempo_imputado_piloto = False
        self.tiempo_imputado_operador = False
        self.tiempo_imputado_supervisor = False
        account_analytic_lines = self.env['account.analytic.line'].search([('idmodelo', '=', self.id),('modelo','=','leulit.vuelo')])
        for item in account_analytic_lines:
            item.unlink()
        return super(ParteVuelo, self).wizardSetPrevuelo()


    # @api.depends('fechavuelo','horasalida','tiempoprevisto','tipo_actividad')
    # def _compute_aa(self):
    #     for item in self:
    #         is_escuela = True if self.parte_escuela_id else False
    #         deltapre = self.env['leulit.item_actividad_aerea'].value_delta_pre
    #         item.aa_until_now_piloto_id = 0
    #         item.aa_until_now_operador = 0
    #         item.aa_until_now_verificado = 0
    #         item.aa_until_now_alumno = 0
    #         item.aa_planned_piloto_id = 0
    #         item.aa_planned_operador = 0
    #         item.aa_planned_verificado = 0
    #         item.aa_planned_alumno = 0
    #         item.aa_max_day_piloto_id = 0
    #         item.aa_max_day_operador = 0
    #         item.aa_max_day_verificado = 0
    #         item.aa_max_day_alumno = 0
            # if item.fechavuelo and item.horasalida:
            #     first_flight_piloto_id = True
            #     first_flight_operador = True
            #     first_flight_verificado = True
            #     first_flight_alumno = True
            #     for vuelo in self.search([('estado','=','cerrado'),('fechavuelo','=',item.fechavuelo)], order="fechavuelo ASC, horasalida ASC"):
            #         tripulacion = ['piloto_id', 'operador', 'verificado', 'alumno']
            #         for tripulante in tripulacion:
            #             if getattr(vuelo, tripulante):
            #                 if getattr(item.piloto_id, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId():
            #                     # Calulamos la actividad aerea hasta ahora con los partes cerrados del dia del piloto del vuelo actual
            #                     if first_flight_piloto_id:
            #                         item.aa_until_now_piloto_id += vuelo.tiemposervicio + deltapre
            #                         first_flight_piloto_id = False
            #                     else:
            #                         item.aa_until_now_piloto_id += vuelo.tiemposervicio
            #                     # Calculamos el tiempo maximo de actividad aerea del dia del piloto del vuelo actual
            #                     if vuelo.tipo_actividad in self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad:
            #                         item.aa_max_day_piloto_id = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ vuelo.tipo_actividad ], item.aa_max_day_piloto_id)
            #                     else:
            #                         if vuelo.parte_escuela_id:
            #                             if vuelo.parte_escuela_id.isvueloato(vuelo.id):
            #                                 item.aa_max_day_piloto_id = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #                             else:
            #                                 item.aa_max_day_piloto_id = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #                         else:
            #                             item.aa_max_day_piloto_id = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad
            #                 if getattr(item.operador, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId():
            #                     # Calulamos la actividad aerea hasta ahora con los partes cerrados del dia del operador del vuelo actual
            #                     if first_flight_operador:
            #                         item.aa_until_now_operador += vuelo.tiemposervicio + deltapre
            #                         first_flight_operador = False
            #                     else:
            #                         item.aa_until_now_operador += vuelo.tiemposervicio
            #                     # Calculamos el tiempo maximo de actividad aerea del dia del piloto del vuelo actual
            #                     if vuelo.tipo_actividad in self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad:
            #                         item.aa_max_day_operador = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ vuelo.tipo_actividad ], item.aa_max_day_operador)
            #                     else:
            #                         if vuelo.parte_escuela_id:
            #                             if vuelo.parte_escuela_id.isvueloato(vuelo.id):
            #                                 item.aa_max_day_operador = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #                             else:
            #                                 item.aa_max_day_operador = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #                         else:
            #                             item.aa_max_day_operador = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad
            #                 if getattr(item.verificado, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId():
            #                     # Calulamos la actividad aerea hasta ahora con los partes cerrados del dia del verificado del vuelo actual
            #                     if first_flight_verificado:
            #                         item.aa_until_now_verificado += vuelo.tiemposervicio + deltapre
            #                         first_flight_verificado = False
            #                     else:
            #                         item.aa_until_now_verificado += vuelo.tiemposervicio
            #                     # Calculamos el tiempo maximo de actividad aerea del dia del piloto del vuelo actual
            #                     if vuelo.tipo_actividad in self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad:
            #                         item.aa_max_day_verificado = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ vuelo.tipo_actividad ], item.aa_max_day_verificado)
            #                     else:
            #                         if vuelo.parte_escuela_id:
            #                             if vuelo.parte_escuela_id.isvueloato(vuelo.id):
            #                                 item.aa_max_day_verificado = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #                             else:
            #                                 item.aa_max_day_verificado = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #                         else:
            #                             item.aa_max_day_verificado = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad
            #                 if getattr(item.alumno, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId():
            #                     # Calulamos la actividad aerea hasta ahora con los partes cerrados del dia del alumno del vuelo actual
            #                     if first_flight_alumno:
            #                         item.aa_until_now_alumno += vuelo.tiemposervicio + deltapre
            #                         first_flight_alumno = False
            #                     else:
            #                         item.aa_until_now_alumno += vuelo.tiemposervicio
            #                     # Calculamos el tiempo maximo de actividad aerea del dia del piloto del vuelo actual
            #                     if vuelo.tipo_actividad in self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad:
            #                         item.aa_max_day_alumno = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ vuelo.tipo_actividad ], item.aa_max_day_alumno)
            #                     else:
            #                         if vuelo.parte_escuela_id:
            #                             if vuelo.parte_escuela_id.isvueloato(vuelo.id):
            #                                 item.aa_max_day_alumno = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #                             else:
            #                                 item.aa_max_day_alumno = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #                         else:
            #                             item.aa_max_day_alumno = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad
            # if item.tipo_actividad:
            #     if item.tipo_actividad in self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad:
            #         item.aa_max_day_piloto_id = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ item.tipo_actividad ], item.aa_max_day_piloto_id)
            #         item.aa_max_day_operador = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ item.tipo_actividad ], item.aa_max_day_operador)
            #         item.aa_max_day_verificado = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ item.tipo_actividad ], item.aa_max_day_verificado)
            #         item.aa_max_day_alumno = max(self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad[ item.tipo_actividad ], item.aa_max_day_alumno)
            #     else:
            #         if item.parte_escuela_id:
            #             if item.parte_escuela_id.isvueloato(item.id):
            #                 item.aa_max_day_piloto_id = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #                 item.aa_max_day_operador = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #                 item.aa_max_day_verificado = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #                 item.aa_max_day_alumno = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-ATO']
            #             else:
            #                 item.aa_max_day_piloto_id = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #                 item.aa_max_day_operador = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #                 item.aa_max_day_verificado = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #                 item.aa_max_day_alumno = self.env['leulit.actividad_aerea'].tiempo_maximo_tipo_actividad['Escuela-noATO']
            #         else:
            #             item.aa_max_day_piloto_id = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad
            #             item.aa_max_day_operador = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad
            #             item.aa_max_day_verificado = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad
            #             item.aa_max_day_alumno = self.env['leulit.actividad_aerea'].default_tiempo_maximo_tipo_actividad

                    
            # # calculamos la actividad aerea prevista con este parte de vuelo y los demas cerrados del dia
            # item.aa_planned_piloto_id = item.tiempoprevisto + (item.aa_until_now_piloto_id if item.aa_until_now_piloto_id > 0 else (item.aa_until_now_piloto_id + deltapre))
            # item.aa_planned_operador = item.tiempoprevisto + (item.aa_until_now_operador if item.aa_until_now_operador > 0 else (item.aa_until_now_operador + deltapre))
            # item.aa_planned_verificado = item.tiempoprevisto + (item.aa_until_now_verificado if item.aa_until_now_verificado > 0 else (item.aa_until_now_verificado + deltapre))
            # item.aa_planned_alumno = item.tiempoprevisto + (item.aa_until_now_alumno if item.aa_until_now_alumno > 0 else (item.aa_until_now_alumno + deltapre))



    tiempo_imputado_piloto = fields.Boolean(string="¿Tiempo imputado?", default=False)
    tiempo_imputado_operador = fields.Boolean(string="¿Tiempo imputado?", default=False)
    tiempo_imputado_supervisor = fields.Boolean(string="¿Tiempo imputado?", default=False)
    # Actividad Aerea
    # aa_until_now_piloto_id = fields.Float(string='Act. Aerea diaria', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_until_now_operador = fields.Float(string='Act. Aerea diaria', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_until_now_verificado = fields.Float(string='Act. Aerea diaria', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_until_now_alumno = fields.Float(string='Act. Aerea diaria', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_planned_piloto_id = fields.Float(string='Act. Aerea diaria prevista', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_planned_operador = fields.Float(string='Act. Aerea diaria prevista', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_planned_verificado = fields.Float(string='Act. Aerea diaria prevista', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_planned_alumno = fields.Float(string='Act. Aerea diaria prevista', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_max_day_piloto_id = fields.Float(string='Act. Aerea max. dia', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_max_day_operador = fields.Float(string='Act. Aerea max. dia', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_max_day_verificado = fields.Float(string='Act. Aerea max. dia', compute=_compute_aa, store=False, digits=(16, 2))
    # aa_max_day_alumno = fields.Float(string='Act. Aerea max. dia', compute=_compute_aa, store=False, digits=(16, 2))


    @api.depends()
    def _account_analytic_lines(self):
        for item in self:
            item.account_analytic_lines = self.env['account.analytic.line'].search([('idmodelo', '=', item.id),('modelo','=','leulit.vuelo')])

    account_analytic_lines = fields.One2many(compute=_account_analytic_lines, comodel_name='account.analytic.line', string='Account Analytic Lines')


    def set_account_analytic_lines_recurrent(self):
        _logger.error("################### set_account_analytic_lines_recurrent ")
        threaded_calculation = threading.Thread(target=self.run_set_account_analytic_lines_recurrent, args=([]))
        _logger.error("################### set_account_analytic_lines_recurrent start thread")
        threaded_calculation.start()

    def run_set_account_analytic_lines_recurrent(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            hoy = datetime.now().strftime("%Y-%m-%d")
            for item in self.search([('estado','=','cerrado'),('fechavuelo','>=',(datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d"))], order="fechavuelo ASC, horasalida ASC"):
                account_analytic_lines = self.env['account.analytic.line'].search([('idmodelo', '=', item.id),('modelo','=','leulit.vuelo')])
                if not account_analytic_lines or len(account_analytic_lines) == 0:
                    item.after_update_create_tiempo_imputado()
                    new_cr.commit()
        _logger.error('################### run_set_account_analytic_lines_recurrent fin thread')


    def set_account_analytic_lines_it(self, fecha=None, codigo=None):
        _logger.error("################### set_account_analytic_lines_it ")
        threaded_calculation = threading.Thread(target=self.run_set_account_analytic_lines_it, args=([fecha,codigo]))
        _logger.error("################### set_account_analytic_lines_it start thread")
        threaded_calculation.start()

    def run_set_account_analytic_lines_it(self, fecha, codigo):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            if codigo:
                for item in self.search([('codigo','like',codigo)]):
                    account_analytic_lines = self.env['account.analytic.line'].search([('idmodelo', '=', item.id),('modelo','=','leulit.vuelo')])
                    if not account_analytic_lines or len(account_analytic_lines) == 0:
                        item.after_update_create_tiempo_imputado()
                        new_cr.commit()
            else:
                for item in self.search([('fechavuelo','>=',fecha),('estado','=','cerrado')]):
                    account_analytic_lines = self.env['account.analytic.line'].search([('idmodelo', '=', item.id),('modelo','=','leulit.vuelo')])
                    if not account_analytic_lines or len(account_analytic_lines) == 0:
                        item.after_update_create_tiempo_imputado()
                        new_cr.commit()
        _logger.error('################### set_account_analytic_lines_it fin thread')
