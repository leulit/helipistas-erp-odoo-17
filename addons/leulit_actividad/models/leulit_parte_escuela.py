# -*- encoding: utf-8 -*-

from optparse import check_builtin
from tabnanny import check
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
import threading
import pytz
from odoo.addons.leulit import utilitylib
from . import actividad_aerea
from . import actividad_laboral

_logger = logging.getLogger(__name__)


class leulit_parte_escuela(models.Model):
    _name           = "leulit.parte_escuela"
    _inherit        = "leulit.parte_escuela"


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
            for parte in self.search([('estado','=','cerrado'),('fecha','>=','2022-01-01')]):
                parte.with_context(context).updDataActividadLaboral()
            new_cr.commit()
            _logger.error("run_upd_datos_actividad fin")


    def updDataActividadLaboral(self):
        for item in self:
            if item.estado == 'cerrado':
                item.write({'estado': 'cerrado'})


    def create_account_line(self, datos):
        try:
            context = dict(self.env.context)
            context.update({
                'not_check_overlap_account_analytic_line': False,
            })
            idaal = self.env["account.analytic.line"].with_context(context).sudo().create(datos)

            sql = "UPDATE account_analytic_line SET date_time = TO_TIMESTAMP('{date_time}','YYYY-MM-DD HH24:MI') WHERE id = {id};".format(
                date_time= datos['date_time'].strftime("%Y-%m-%d %H:%M") ,
                id = idaal.id
            )
            self._cr.execute(sql)
            self._cr.commit()
            for item in self:
                if item.fecha != datetime.now().date():
                    self.env['leulit.actividad_aerea_no_introducida'].create({'fecha': item.fecha})
        except Exception as exc:
            import traceback
            import json
            self.env.cr.rollback()
            strtraceback = traceback.format_exc()
            _logger.error("*********> ERROR read = %r",strtraceback)
            fecha = fields.Datetime.now()       
            self.env['leulit.error_import'].sudo().create({
                'tabla' : "account.analytic.line",
                'datos' : datos['name'],
                'comments' : "ERROR CREANDO TIMESHEET PARTE DE ESCUELA",
                'fecha' : fecha
            })
            raise ValidationError("Antes de cerrar el parte de escuela, revisa circulares, partes de escuela como alumno y reuniones.")


    def getDateTimeUTC(self, fecha, hora):
        try:
            date2 = utilitylib.leulit_float_time_to_str( hora )
            date1 = fecha.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            valor = datetime.strptime(tira,"%Y-%m-%d %H:%M")
            madrid_tz = pytz.timezone("Europe/Madrid")
            mtz = madrid_tz.localize(datetime(valor.year, valor.month, valor.day, valor.hour, valor.minute))
            dt_utc = mtz.astimezone(pytz.timezone('UTC'))
            return dt_utc.replace(tzinfo=None)
        except Exception as e:
            _logger.error("_date_end_utc %r",e)
            return None


    def updDataActividadLaboralByEmployeeId(self, employee_id, partner_id):
        _logger.error('######## func updDataActividadLaboralByEmployeeId')
        idproject = self.env['ir.config_parameter'].sudo().get_param('leulit.school_hours_project')
        for item in self:
            datos = {
                "date_time": item.getDateTimeUTC( item.fecha, item.hora_start ),
                "unit_amount": item.tiempo,
                "date": item.fecha,
                "project_id": int(idproject),
                "name": item.name,
                "ref": item.id,
                "partner_id": partner_id,
                "employee_id": employee_id,
                'modelo' : 'leulit.parte_escuela',
                'idmodelo' : item.id,
                'product_uom_id' : 4,
            }
            _logger.error("--->updDataActividadLaboralByEmployeeId---> datos = %r",datos)
            self.create_account_line(datos)

    
    def write(self, values):
        res = super(leulit_parte_escuela, self).write(values)
        if 'estado' in values:
            if values['estado'] == 'cerrado' or self.estado == 'cerrado':
                if not self.vuelo_id:
                    if ((self.sudo().profesor) and (self.sudo().profesor.employee)):
                        result = self.env['account.analytic.line'].search( [('idmodelo','=',self.id),('modelo','=','leulit.parte_escuela'),('employee_id','=',self.sudo().profesor.employee.id)] )
                        if not result and not self.tiempo_imputado:
                            self.updDataActividadLaboralByEmployeeId( self.sudo().profesor.employee.id, self.sudo().profesor.getPartnerId())
                            self.tiempo_imputado = True

                    if ((self.sudo().profesoradjunto) and (self.sudo().profesoradjunto.employee)):
                        result = self.env['account.analytic.line'].search( [('idmodelo','=',self.id),('modelo','=','leulit.parte_escuela'),('employee_id','=',self.sudo().profesoradjunto.employee.id)] )
                        if not result and not self.tiempo_imputado_profesor_adjunto:
                            self.updDataActividadLaboralByEmployeeId( self.sudo().profesoradjunto.employee.id, self.sudo().profesoradjunto.getPartnerId())
                            self.tiempo_imputado_profesor_adjunto = True

        return res


    @api.depends()
    def _account_analytic_lines(self):
        for item in self:
            item.account_analytic_lines = self.env['account.analytic.line'].search([('idmodelo', '=', item.id),('modelo','=','leulit.parte_escuela')])


    def updDataActividad(self, item):
        _logger.error("---> updDataActividad")                
        # CADENA PROCESAMIENTO ACTIVIDAD LABORAL
        handlerAL = item.initChainActividadLaboral()
        _logger.error("---> handlerAL = %r",handlerAL)        
        request = actividad_laboral.ActividadLaboralChainRequest()
        request.env = self.env
        request.fecha = item.fecha
        request.inicio = item.hora_start
        request.fin = item.hora_end
        request.partner = item.profesor.getPartnerId()
        request.tiempo = item.tiempo
        request.idmodelo = item.id
        request.modelo = 'leulit.parte_escuela'
        request.escuela = True
        request.ato = True if item.vuelo_id and item.isvueloato(item.vuelo_id.id) else False
        handlerAL.handle(request)

        # CADENA PROCESAMIENTO ACTIVIDAD AEREA
        handlerAA = item.initChainActividadAerea()        
        _logger.error("---> updDataActividad = %r",request.fecha)        
        request = actividad_aerea.ActividadAereaChainRequest()
        request.env = self.env
        request.fecha = item.fecha
        request.inicio = item.hora_start
        request.fin = item.hora_end
        request.partner = item.profesor.getPartnerId()
        request.tiempo = item.tiempo
        request.idmodelo = item.id
        request.modelo = 'leulit.parte_escuela'        
        request.escuela = True
        request.ato = True if item.vuelo_id and item.isvueloato(item.vuelo_id.id) else False
        handlerAA.handle(request)

 

    def updDataActividadFecha(self, fecha):
        items = self.search([('fecha','=',fecha),('estado','=','cerrado')])
        _logger.error("parte_escuela updDataActividadFecha items = %r",items)
        if len(items) > 0:
            self.updDataActividad(items)
            

    account_analytic_lines = fields.One2many(compute=_account_analytic_lines, comodel_name='account.analytic.line', string='Account Analytic Lines')
    tiempo_imputado = fields.Boolean(string="¿Tiempo imputado?", default=False)
    tiempo_imputado_profesor_adjunto = fields.Boolean(string="¿Tiempo imputado?", default=False)


    def imputar_tiempo_profesor(self):
        parte = self
        if not parte.vuelo_id:
            if ((parte.sudo().profesor) and (parte.sudo().profesor.employee)):
                parte.updDataActividadLaboralByEmployeeId( parte.sudo().profesor.employee.id, parte.sudo().profesor.getPartnerId())
                parte.tiempo_imputado = True


    def imputar_tiempo_profesor_adjunto(self):
        parte = self
        if not parte.vuelo_id:
            if ((parte.sudo().profesoradjunto) and (parte.sudo().profesoradjunto.employee)):
                    parte.updDataActividadLaboralByEmployeeId( parte.sudo().profesoradjunto.employee.id, parte.sudo().profesoradjunto.getPartnerId())
                    parte.tiempo_imputado_profesor_adjunto = True


    # Recalcular todos los partes de escuela cerrados para que se imputen todos los tiempos.. 
    def recalcular_tiempos_imputados(self):
        _logger.error("recalcular_tiempos_imputados ")
        threaded_calculation = threading.Thread(target=self.run_recalcular_tiempos_imputados, args=([]))
        _logger.error("recalcular_tiempos_imputados start thread")
        threaded_calculation.start()
        return {}

    def run_recalcular_tiempos_imputados(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            for parte in self.search([('estado','=','cerrado'),('fecha','>=','2025-01-01')]):
                if not parte.vuelo_id:
                    if ((parte.sudo().profesor) and (parte.sudo().profesor.employee)):
                        result = self.env['account.analytic.line'].search( [('idmodelo','=',parte.id),('modelo','=','leulit.parte_escuela'),('employee_id','=',parte.sudo().profesor.employee.id)] )
                        if not result and not parte.tiempo_imputado:
                            parte.updDataActividadLaboralByEmployeeId( parte.sudo().profesor.employee.id, parte.sudo().profesor.getPartnerId())
                            parte.tiempo_imputado = True
                        if result and not parte.tiempo_imputado:
                            parte.tiempo_imputado = True

                    if ((parte.sudo().profesoradjunto) and (parte.sudo().profesoradjunto.employee)):
                        result = self.env['account.analytic.line'].search( [('idmodelo','=',parte.id),('modelo','=','leulit.parte_escuela'),('employee_id','=',parte.sudo().profesoradjunto.employee.id)] )
                        if not result and not parte.tiempo_imputado_profesor_adjunto:
                            parte.updDataActividadLaboralByEmployeeId( parte.sudo().profesoradjunto.employee.id, parte.sudo().profesoradjunto.getPartnerId())
                            parte.tiempo_imputado_profesor_adjunto = True
                        if result and not parte.tiempo_imputado_profesor_adjunto:
                            parte.tiempo_imputado_profesor_adjunto = True
            new_cr.commit()
            _logger.error("recalcular_tiempos_imputados fin")

        