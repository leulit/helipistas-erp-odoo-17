# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
import pytz
import calendar
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp
import threading
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

from . import actividad_aerea
from . import actividad_laboral

import logging
_logger = logging.getLogger(__name__)



class ActividadAerea(models.Model):
    _name = "leulit.actividad_aerea"
    _description = "Actividad Aerea"
    _order = 'fecha DESC, inicio ASC'

    tiempo_maximo_tipo_actividad = {
        'AOC'               : 8.5,
        'Trabajo Aereo'     : 11.0,
        'LCI'               : 11.0,
        'Escuela-ATO'       : 8.0,
        'Escuela-noATO'     : 11.0,
    }
    default_tiempo_maximo_tipo_actividad = 11.0


    descanso_minimo = 10.5
    descanso_parcial_min = 3.0
    descanso_parcial_max = 8.0

    _str_time_flight_range1 = "28d"  
    _str_time_flight_range2 = "12m"
    _str_time_flight_range3 = "3_28d"
    _str_dias_mes = "dias_mes"

    _max_horas_28d = 100
    _max_horas_12m = 900
    _max_horas_3p28d = 270
    _max_dias_mes = 22

    @api.depends('fecha','inicio')
    def _fecha_inicio(self):
        for item in self:
            date2 = utilitylib.leulit_float_time_to_str( item.inicio )
            date1 = item.fecha.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            item.fecha_inicio = datetime.strptime(tira,"%Y-%m-%d %H:%M")

    @api.depends('fecha','fin')
    def _fecha_fin(self):
        for item in self:
            date2 = utilitylib.leulit_float_time_to_str( item.fin )
            date1 = item.fecha.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            item.fecha_fin = datetime.strptime(tira,"%Y-%m-%d %H:%M")


    @api.depends('time_flight_range1')
    def _valid_time_flight_range1(self):
        for item in self:
            item.valid_time_flight_range1 = "red" if item.time_flight_range1 > self._max_horas_28d else "green"

    def _time_flight_range1(self):
        for item in self:
            fechas = self.getFechaIniPeriodo(self._str_time_flight_range1, item.fecha)
            items = self.env['leulit.item_actividad_aerea'].search( [('partner','=',item.partner.id), ('fecha','>=',fechas['fecha_ini']), ('fecha','<=',fechas['fecha_fin']), ('modelo','=','leulit.vuelo')], order = 'fecha DESC, inicio ASC' )
            valor = 0
            for item2 in items:
                valor += item2.tiempo
            item.time_flight_range1 = valor

    @api.depends('time_flight_range2')
    def _valid_time_flight_range2(self):
        for item in self:
            item.valid_time_flight_range2 = "red" if item.time_flight_range2 > self._max_horas_12m else "green"

    def _time_flight_range2(self):
        for item in self:
            fechas = self.getFechaIniPeriodo(self._str_time_flight_range2, item.fecha)
            items = self.env['leulit.item_actividad_aerea'].search( [('partner','=',item.partner.id), ('fecha','>=',fechas['fecha_ini']), ('fecha','<=',fechas['fecha_fin']), ('modelo','=','leulit.vuelo')], order = 'fecha DESC, inicio ASC' )
            valor = 0
            for item2 in items:
                valor += item2.tiempo
            item.time_flight_range2 = valor


    @api.depends('time_flight_range3')
    def _valid_time_flight_range3(self):       
        for item in self:            
            item.valid_time_flight_range3 = "red" if item.time_flight_range3 > self._max_horas_3p28d else "green"

    def _time_flight_range3(self):
        for item in self:
            fechas = self.getFechaIniPeriodo(self._str_time_flight_range3, item.fecha)
            items = self.env['leulit.item_actividad_aerea'].search( [('partner','=',item.partner.id), ('fecha','>=',fechas['fecha_ini']), ('fecha','<=',fechas['fecha_fin']), ('modelo','=','leulit.vuelo')], order = 'fecha DESC, inicio ASC' )
            valor = 0
            for item2 in items:
                valor += item2.tiempo
            item.time_flight_range3 = valor



    @api.depends('tiempo')
    def _valid_activity_time(self):
        for item in self:
            item.valid_activity_time = "red" if item.tiempo > item.max_duracion else "green"


    @api.depends('dias_trabajados_mes')
    def _valid_dias_trabajados_mes(self):
        for item in self:
            max_dias_mes = (calendar.monthrange(item.fecha.year,item.fecha.month)[1])-8
            item.valid_dias_trabajados_mes = "red" if item.dias_trabajados_mes > max_dias_mes else "green"


    def aplica_descanso_parcial(self):
        self.aplica_desc_parcial = True
        self.env['leulit.vuelo'].upd_datos_actividad(self.fecha,self.fecha)


    def no_aplica_descanso_parcial(self):
        self.aplica_desc_parcial = False
        self.env['leulit.vuelo'].upd_datos_actividad(self.fecha,self.fecha)

    @api.depends('partner')
    def _get_user_from_partner(self):
        for item in self:
            item.user_id = False
            if item.partner.user_ids:
                item.user_id = item.partner.user_ids[0]

    def _search_user_from_partner(self, operator, value):
        query = """
            SELECT DISTINCT laa.id 
            FROM leulit_actividad_aerea laa
            WHERE laa.partner = %s
        """
        self.env.cr.execute(query, (self.env.user.partner_id.id,))
        aa = [r[0] for r in self.env.cr.fetchall()]
        
        if aa:
            return [('id', 'in', aa)]
        return [('id', '=', False)]

    fecha = fields.Date('Fecha', index=True)
    fecha_inicio = fields.Datetime(string="Fecha inicio",compute=_fecha_inicio, store=False)
    fecha_fin = fields.Datetime(string="Fecha fin",compute=_fecha_fin, store=False)
    inicio = fields.Float('Inicio actividad', digits=(16, 2))
    fin = fields.Float('Fin actividad', digits=(16, 2))
    tiempo_amplia = fields.Float('Tiempo ampliación', digits=(16, 2))
    airtime = fields.Float('Airtime', digits=(16, 2))
    tiempo_vuelo = fields.Float('Tiempo de vuelo', digits=(16, 2))
    tiempo_desc_parcial = fields.Float('Tiempo descanso parcial', digits=(16, 2))
    aplica_desc_parcial = fields.Boolean(string="Aplica descanso parcial")
    max_duracion = fields.Float('Tiempo máximo actividad', digits=(16, 2))
    tiempo = fields.Float("Tiempo actividad", digits=(16, 2))
    partner = fields.Many2one('res.partner', 'Empleado Helipistas', ondelete='restrict', index=True)
    user_id = fields.Many2one(comodel_name='res.users', string='Usuario', compute=_get_user_from_partner, search=_search_user_from_partner, store=False)
    descripcion = fields.Char('Descripción')
    valid_activity_time = fields.Char(string='Tiempo actividad valido', compute=_valid_activity_time, store=False)
    dias_trabajados_mes = fields.Integer(string="Días trabajados mes")
    valid_dias_trabajados_mes = fields.Char(string='28 d. ok', compute=_valid_dias_trabajados_mes, store=False)

    #time_flight_range1 = fields.Float(string="TV 28d",type="float", digits=(16, 2))
    time_flight_range1 = fields.Float(string='28 d. ok', compute=_time_flight_range1, digits=(16, 2), store=False)
    valid_time_flight_range1 = fields.Char(string='28 d. ok', compute=_valid_time_flight_range1, store=False)
    
    #time_flight_range2 = fields.Float(string="TV 12 m.",type="float", digits=(16, 2))
    time_flight_range2 = fields.Float(string='TV 12 m.', compute=_time_flight_range2, digits=(16, 2), store=False)
    valid_time_flight_range2 = fields.Char(string='12 m. ok', compute=_valid_time_flight_range2, store=False)

    #time_flight_range3 = fields.Float(string="TV 3 m.",type="float", digits=(16, 2))
    time_flight_range3 = fields.Float(string='3 m. ok', compute=_time_flight_range3, digits=(16, 2), store=False)
    valid_time_flight_range3 = fields.Char(string='3 m. ok', compute=_valid_time_flight_range3, store=False)
    
    ato = fields.Boolean('ato')
    prevista = fields.Boolean('Prevista')


    def check_overlap(self, iditem, fecha, fecha_inicio, fecha_fin, partner):
        isOverlapping = False
        for item in self.search( [('id','!=',iditem), ('fecha','=',fecha), ('partner','=',partner)] ):
            if item.fecha_fin:
                isOverlapping =  (
                    (item.fecha_inicio  <= fecha_fin)
                    and
                    (fecha_inicio <= item.fecha_fin)
                    and
                    (item.fecha_inicio  <= item.fecha_fin)
                    and
                    (fecha_inicio  <= fecha_fin)
                )
            else:
                if item.fecha_inicio and fecha_fin:
                    isOverlapping =  (
                        (item.fecha_inicio  <= fecha_fin)
                        and
                        (fecha_inicio  <= item.fecha_inicio)
                    )      
            if (isOverlapping):
                break
        return isOverlapping


    def enoughRestMin(self, partner, fecha):
        result = False
        for item in self.search( [('partner','=',partner)], limit = 1, order = 'fecha_fin DESC' ):
            duration = fecha - item.fecha_fin
            result = (duration.total_seconds() / 60) > self.env['leulit.item_actividad_aerea'].getMinRestMin()
        return result


    def getFechaIniPeriodo(self, periodo, fecha):
        d2 = fecha
        d1 = fecha
        if periodo == self._str_time_flight_range1:
            d1 = d2 - relativedelta(days=28)
        if periodo == self._str_time_flight_range3:
            d1 = d2 - relativedelta(days=(28*3))
        if periodo == self._str_time_flight_range2:
            d1 = d2 - relativedelta(months=12)
        if periodo == self._str_dias_mes:
            fechasMonth = utilitylib.startEndMonth( objfecha = fecha )
            d1 = fechasMonth['startmonth']
            d2 = fechasMonth['endmonth']
        return {
            'fecha_ini': d1,
            'fecha_fin': d2
        }


    def detalle_av(self):
        items = self.env['leulit.item_actividad_aerea'].search( [('partner','=',self.partner.id), ('fecha','=',self.fecha)], order = 'fecha DESC, inicio ASC' )        
        return {
            'type': 'ir.actions.act_window',
            'name': "Detalle {0}".format(self.fecha),
            'res_model': 'leulit.item_actividad_aerea',
            'view_id': self.env.ref('leulit_actividad.leulit_202204290852_tree').id,
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [('id', 'in', items.ids)],
        }       

    def detalle_timerange(self, range):
        self.ensure_one()
        context = dict(self.env.context or {})
        fechas = self.getFechaIniPeriodo(range, self.fecha)

        items = self.env['leulit.item_actividad_aerea'].search( [('partner','=',self.partner.id), ('fecha','>=',fechas['fecha_ini']), ('fecha','<=',fechas['fecha_fin']), ('modelo','=','leulit.vuelo')], order = 'fecha DESC, inicio ASC' )        
        if range == "dias_mes":
            items = self.env['leulit.item_actividad_aerea'].search( [('partner','=',self.partner.id), ('fecha','>=',fechas['fecha_ini']), ('fecha','<=',fechas['fecha_fin'])], order = 'fecha DESC, inicio ASC' )        
        ##items = self.env['leulit.item_actividad_aerea'].search( [('partner','=',self.partner.id), ('fecha','=',self.fecha)], order = 'fecha DESC, inicio ASC' )        
        return {
            'type': 'ir.actions.act_window',
            'name': "Detalle {0} - {1}".format(fechas['fecha_ini'], fechas['fecha_fin']),
            'res_model': 'leulit.item_actividad_aerea',
            'view_id': self.env.ref('leulit_actividad.leulit_202204290852_tree').id,
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [('id', 'in', items.ids)],
        }       

    def detalle_timerange_1(self):
        return self.detalle_timerange(self._str_time_flight_range1)

    def detalle_timerange_2(self):
        return self.detalle_timerange(self._str_time_flight_range2)

    def detalle_timerange_3(self):
        return self.detalle_timerange(self._str_time_flight_range3)

    def detalle_dias_mes(self):
        return self.detalle_timerange(self._str_dias_mes)
