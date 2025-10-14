# -*- encoding: utf-8 -*-

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


class AnalyticActividadAearea(models.Model):
    _name = "leulit.analytic_actividad_aerea"
    _description = "Análisis Actividad Aerea"


    fecha = fields.Date('Fecha', index=True)
    partner = fields.Many2one('res.partner', 'Empleado Helipistas', ondelete='restrict', index=True)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"


    def unlink(self):
        fecha = False
        for item in self:
            if item.guardia:
                partner = self.env['res.partner'].search([('user_ids','=',item.employee_id.user_id.id)])
                line = self.env['leulit.item_actividad_aerea'].search([('partner','=',partner.id), ('modelo','=','account.analytic.line'), ('idmodelo','=',item.id)])
                fecha = line.fecha
                line.unlink()
                lines = self.env['leulit.item_actividad_aerea'].search([('partner','=',partner.id), ('fecha','=',fecha)])
                if not lines:
                    day = self.env['leulit.actividad_aerea'].search([('fecha','=',fecha),('partner','=',partner.id)])
                    day.unlink()
            if fecha:
                self.upd_datos_actividad(fecha_origen=fecha.strftime("%Y-%m-%d"),fecha_fin='2050-01-01',id_line=item.id)
                self.env['leulit.vuelo'].upd_datos_actividad(fecha_origen=fecha.strftime("%Y-%m-%d"),fecha_fin='2050-01-01')
            return super(AccountAnalyticLine, item).unlink()


    def write(self, values):
        res = super(AccountAnalyticLine, self).write(values)
        if self.guardia:
            self.updDataActividadAerea()
        return res
        

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

    
    def verificar_actividad_aerea(self, fecha, partner):
        o_aa = self.env['leulit.actividad_aerea']
        o_vul = self.env['leulit.vuelo']

        vuls = o_vul.search([('estado','=','cerrado'),('fechavuelo','=',fecha),'|','|','|',('piloto_id','=',partner.getPiloto()),('operador','=',partner.getOperador()),('verificado','=',partner.getPiloto()),('alumno','=',partner.getAlumno())], order="fechavuelo ASC, horasalida ASC")
        if vuls:
            items_vul = o_vul.search(['|',('id','in',vuls.ids),('id','=',self.id)])
        else:
            items_vul = o_vul.search([('id','=',self.id)])
        max_duracion = 0.0
        tiempo_desc_parcial = 0.0
        tiempo_amplia = 0.0
        inicioitems = 1111.0
        finitems = 0.0
        incremento = 0.0
        airtime = 0.0
        tiempo_vuelo = 0.0
        for index,itemvul in enumerate(items_vul):
            airtime += itemvul.airtime
            tiempo_vuelo += itemvul.tiemposervicio

            #cálculo tiempo máxima de actividad
            if itemvul.tipo_actividad in o_aa.tiempo_maximo_tipo_actividad:
                max_duracion = max(o_aa.tiempo_maximo_tipo_actividad[ itemvul.tipo_actividad ], max_duracion)
            else:
                if itemvul.parte_escuela_id:
                    if itemvul.parte_escuela_id.isvueloato(itemvul.id):
                        max_duracion = o_aa.tiempo_maximo_tipo_actividad['Escuela-ATO']
                    else:
                        max_duracion = o_aa.tiempo_maximo_tipo_actividad['Escuela-noATO']
                else:
                    max_duracion = o_aa.default_tiempo_maximo_tipo_actividad
            #cálculos descanso parcial
            if (index > 0):
                itemaaAnt = items_vul[index-1]
                intervalo = round(float(itemvul.horasalida),2) - round(float(itemaaAnt.horallegada),2)
                if intervalo >= o_aa.descanso_parcial_min and intervalo <= o_aa.descanso_parcial_max:
                    if intervalo > o_aa.descanso_parcial_max:
                        intervalo = 8.0
                    incremento = round((intervalo / 2.0),2)
                
                    tiempo_desc_parcial = tiempo_desc_parcial + intervalo
                    tiempo_amplia = tiempo_amplia + incremento

            inicioitems = min(inicioitems, itemvul.horasalida)
            finitems = max(finitems, itemvul.horallegada)

        if (max_duracion + tiempo_amplia) >= (finitems - inicioitems):
            return True
        
        return False


    def updDataActividadAerea(self):
        if self.employee_id.user_id.has_group("leulit.ROperaciones_operador") or self.employee_id.user_id.has_group("leulit.RCampaña_operador"):
            # full_actividad_aerea = False
            # who = False
            # # si verificar_actividad_aerea devuelve TRUE se puede acabar de imputar tiempo, si devuelve FALSE pasa el tiempo de actividad aerea, y se debera gestionar una ocurrencia.
            # partner = self.env['res.partner'].search([('user_ids','=',self.employee_id.user_id.id)])
            # if partner:
            #     if not self.verificar_actividad_aerea(self.date_time.date(), partner):
            #         full_actividad_aerea = True
            #         who = partner
            
            # if full_actividad_aerea:
            #     view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_esignature.leulit_202306071553_form')
            #     view_id = view_ref and view_ref[1] or False
            #     return {
            #         'type': 'ir.actions.act_window',
            #         'name': 'Crear Ocurrencia',
            #         'res_model': 'wizard_create_claim_from_vuelo',
            #         'view_mode': 'form',
            #         'view_id': view_id,
            #         'target': 'new',
            #         'context': {'default_vuelo': self.id, 'default_who':who.id}
            #     }
            # else:
            _logger.error("--->updDataActividadAerea---> %r",self)
            handlerAA = self.initChainActividadAerea()
            request = actividad_aerea.ActividadAereaChainRequest()
            request.env = self.env
            request.fecha = self.date_time.astimezone(pytz.timezone('UTC')).date()
            request.inicio = utilitylib.leulit_datetime_to_float_time(self.date_time.astimezone(pytz.timezone("Europe/Madrid")))
            request.horallegada = False
            request.tiempo = self.unit_amount
            request.airtime = 0
            request.idmodelo = self.id
            request.prevista = False
            request.modelo = 'account.analytic.line'
            request.descripcion = self.name
            request.tipo_actividad = self.vuelo_tipo_act_id if self.vuelo_no_hlp else False
            request.escuela = False
            request.ato = False
            request.env = self.env
            request.partner = self.env['res.partner'].search([('user_ids','=',self.employee_id.user_id.id)]).id
            request.rol = "piloto" if self.vuelo_no_hlp else "Empleado"
            handlerAA.handle(request)


    @api.constrains('employee_id','date_time','date_time_end')
    def _check_overlap_task(self):
        overlap = False
        for record in self:
            
            if (('not_check_overlap_account_analytic_line' not in self.env.context) or (not self.env.context['not_check_overlap_account_analytic_line'])):                
                for item in self.env['account.analytic.line'].search( [('id','!=',record.id), ('date','=',record.date), ('employee_id','=',record.employee_id.id)] ):
                    isOverlapping = False
                    if item.date_time_end:
                        if record.date_time_end:
                            isOverlapping =  (
                                (record.date_time  <= item.date_time_end)
                                and
                                (item.date_time  <= record.date_time_end)
                                and
                                (record.date_time  <= record.date_time_end)
                                and
                                (item.date_time  <= item.date_time_end)
                            )
                        else:
                            if record.date_time and item.date_time_end:
                                isOverlapping =  (
                                    (record.date_time  <= item.date_time_end)
                                    and
                                    (item.date_time  <= record.date_time)
                                )
                    '''
                    if isOverlapping:
                        raise ValidationError("Ya existe una imputación de tiempo para este empleado y periodo. Tarea: %s Descripción: %s" % (item.task_id.code, item.name))
                    '''
    
    def upd_datos_actividad(self, fecha_origen, fecha_fin, id_line=None):
        _logger.error("upd_datos_actividad ")        
        threaded_calculation = threading.Thread(target=self.run_upd_datos_actividad, args=([fecha_origen,fecha_fin,id_line]))
        _logger.error("upd_datos_actividad start thread")
        threaded_calculation.start()
        return {}

    def run_upd_datos_actividad(self, fecha_origen, fecha_fin, id_line):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)

            _logger.error('run_upd_datos_actividad start loop')
            
            domains = [
                [('date_time','>=',datetime.now().strftime("%Y-%m-%d")),('date_time','<=',datetime.now().strftime("%Y-%m-%d"))],
            ]
            if fecha_origen and fecha_fin:
                if id_line:
                    domains = [
                        [('date_time','>=',fecha_origen),('date_time','<=',fecha_fin),('id','!=',id_line),('guardia','=',True)]
                    ]
                else:
                    domains = [
                        [('date_time','>=',fecha_origen),('date_time','<=',fecha_fin),('guardia','=',True)]
                    ]
            _logger.error("---> START UPD DOMAINS %r",domains)

            for domain in domains:
                _logger.error("---> START UPD DOMAIN %r",domain)
                for parte in self.search(domain, order="date_time ASC"):
                    parte.with_context(context).updDataActividadAerea()
            new_cr.commit()
            new_cr.close()
            _logger.error("run_upd_datos_actividad fin")


    def _get_tipo_trabajo(self):
        return (
            ('AOC', 'AOC'),
            ('Trabajo Aereo', 'Trabajo Aereo'),
            ('Escuela', 'Escuela'),
            ('LCI', 'LCI'),
            ('NCO', 'NCO'),
        )

    def get_tipos_actividad(self):
        return {
            'AOC':'AOC',
            'Trabajo Aereo':'Trabajo Aereo',
            'Escuela':'Escuela',
            'LCI':'LCI',
            'NCO':'NCO',
        }

    #partner para relacionar horas imputadas con pilotos, alumnos, etc..
    leulit_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Custom Partner",
    )
    idmodelo = fields.Integer('idmodelo')
    ruta = fields.Boolean('Ruta')
    guardia = fields.Boolean('Guardia')
    # Vuelos para fuera de HLP y rellenar actividad aerea
    vuelo_no_hlp = fields.Boolean(string="Vuelo NO helipistas")
    vuelo_tipo_act_id = fields.Selection(_get_tipo_trabajo, 'Actividad vuelo')

    modelo = fields.Char('Modelo')
    #partner para relacionar horas imputadas con pilotos, alumnos, etc..
    leulit_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Custom Partner",
    )
    byday_id = fields.Many2one('leulit.account.analytic.line.byday','Información diaria',ondelete='restrict')
    checklist_id = fields.Many2one(comodel_name='leulit.checklist', string='Checklist')
    date_time = fields.Datetime('Fecha y hora inicio')