# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

_actividades = []
_planificada = False

class leulit_actividad_16bravo_dia_planificada(models.Model):
    _name = "leulit.actividad_16bravo_dia_planificada"
    _inherit = "leulit.actividad_16bravo_dia"
    _description = "leulit_actividad_16bravo_dia_planificada"
    _auto = False
    _order = "fecha asc"

    _max_horas_28d = 100
    _max_horas_12m = 900
    _max_horas_3p28d = 270
    _max_dias_mes = 22


    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'leulit_actividad_16bravo_dia_planificada')
        self._cr.execute(""" CREATE OR REPLACE VIEW leulit_actividad_16bravo_dia_planificada AS 
            (
                 SELECT * FROM leulit_actividad_16bravo_dia WHERE prevista = 't' ORDER BY fecha ASC
            )
        """)
    

    def _time_flight_range1_plan(self):
        for item in self:
            sql = '''
                SELECT 
			            round(coalesce(SUM(T1.tiempo_vuelo),0),2) as total
		            FROM 
			            leulit_actividad_16bravo as T1
		            WHERE 
			            T1.fecha >= ('{0}'::DATE - (INTERVAL '28 DAY'))
		            AND
			            T1.fecha <= '{0}'::DATE
		            AND
			            T1.partner = {1}
            '''.format(item.fecha, item.partner.id)
            row = utilitylib.runQueryReturnOne(self._cr, sql)        
            item.time_flight_range1_plan = row['total']

    def _time_flight_range2_plan(self):
        for item in self:
            sql = '''
                SELECT 
			            round(coalesce(SUM(T1.tiempo_vuelo),0),2) as total
		            FROM 
			            leulit_actividad_16bravo as T1
		            WHERE 
			            T1.fecha >= ('{0}'::DATE - (INTERVAL '12 MONTH'))
		            AND
			            T1.fecha <= '{0}'::DATE
		            AND
			            T1.partner = {1}
            '''.format(item.fecha, item.partner.id)
            row = utilitylib.runQueryReturnOne(self._cr, sql)        
            item.time_flight_range2_plan = row['total']

    def _time_flight_range3_plan(self):
        for item in self:
            sql = '''
                SELECT 
			            round(coalesce(SUM(T1.tiempo_vuelo),0),2) as total
		            FROM 
			            leulit_actividad_16bravo as T1
		            WHERE 
			            T1.fecha >= ('{0}'::DATE - (INTERVAL '84 DAY'))
		            AND
			            T1.fecha <= '{0}'::DATE
		            AND
			            T1.partner = {1}
            '''.format(item.fecha, item.partner.id)
            row = utilitylib.runQueryReturnOne(self._cr, sql)        
            item.time_flight_range3_plan = row['total']        

    def _valid_time_flight_range1_plan(self):
        for item in self:
            item.valid_time_flight_range1_plan = "red" if item.time_flight_range1_plan > self._max_horas_28d else "green"
            
    def _valid_time_flight_range2_plan(self):
        for item in self:
            item.valid_time_flight_range2_plan = "red" if item.time_flight_range2_plan > self._max_horas_12m else "green"

    def _valid_time_flight_range3_plan(self):
        for item in self:
            item.valid_time_flight_range3_plan = "red" if item.time_flight_range3_plan > self._max_horas_3p28d else "green"   

    def _dias_tabajados_mes(self):
        for item in self:
            year = utilitylib.str_date_format( item.fecha, formatDestino="%Y")
            month = utilitylib.str_date_format( item.fecha, formatDestino="%m")
            sql = '''
                 SELECT 
			            count(id) as dias_tabajados_mes
		            FROM 
			            leulit_actividad_16bravo_dia
		            WHERE 
			            fecha < '{0}'::DATE
                    AND
                        to_char(fecha,'MM') = '{2}'
                    AND
                        to_char(fecha,'yyyy') = '{3}'
		            AND
			            partner = {1}
                    AND
                        prevista = 'f'
                    LIMIT 1
            '''.format(item.fecha, item.partner.id, month, year)            
            row = utilitylib.runQueryReturnOne(self._cr, sql)    
            if row and 'dias_tabajados_mes' in row:    
                item.dias_tabajados_mes = row['dias_tabajados_mes']
            else:
                item.dias_tabajados_mes = 0

    def _dias_programados_mes(self):
        for item in self:
            year = utilitylib.str_date_format( item.fecha, formatDestino="%Y")
            month = utilitylib.str_date_format( item.fecha, formatDestino="%m")
            sql = '''
                SELECT 
			            count(id) as dias_programados_mes
		            FROM 
			            leulit_actividad_16bravo_dia
		            WHERE 
			            fecha >= '{0}'::DATE
                    AND
                        to_char(fecha,'MM') = '{2}'
                    AND
                        to_char(fecha,'yyyy') = '{3}'
		            AND
			            partner = {1}                    
                    AND
                        prevista = 't'
            '''.format(item.fecha, item.partner.id, month, year)
            row = utilitylib.runQueryReturnOne(self._cr, sql)        
            if row and 'dias_programados_mes' in row:
                item.dias_programados_mes = row['dias_programados_mes']
            else:
                item.dias_programados_mes = 0


    def _dias_trab_ano(self):
        for item in self:
            year = utilitylib.str_date_format( item.fecha, formatDestino="%Y")
            sql = '''
                SELECT 
			            count(id) as dias_trabajados_ano
		            FROM 
			            leulit_actividad_16bravo_dia
		            WHERE 
			            fecha < '{0}'::DATE
                    AND
                        to_char(fecha,'yyyy') = '{2}'
		            AND
			            partner = {1}                    
                    AND
                        prevista = 'f'
            '''.format(item.fecha, item.partner.id, year)
            row = utilitylib.runQueryReturnOne(self._cr, sql)                    
            if row and 'dias_trabajados_ano' in row:
                item.dias_trab_ano = row['dias_trabajados_ano']
            else:
                item.dias_trab_ano = 0

    def _dias_programados_ano(self):
        for item in self:
            year = utilitylib.str_date_format( item.fecha, formatDestino="%Y")
            sql = '''
                SELECT 
			            count(id) as dias_programados_ano
		            FROM 
			            leulit_actividad_16bravo_dia
		            WHERE 
			            fecha >= '{0}'::DATE
                    AND
                        date_part('year', fecha) = {2}
		            AND
			            partner = {1}                    
                    AND
                        prevista = 't'
            '''.format(item.fecha, item.partner.id, year)
            row = utilitylib.runQueryReturnOne(self._cr, sql)        
            if row and 'dias_programados_ano' in row:
                item.dias_programados_ano = row['dias_programados_ano']
            else:
                item.dias_programados_ano = 0



    # def _uid_ok(self, cr, uid, ids, field_name, field_args,  context=None):       
    #     res = {}
    #     for item in self.read(cr, uid, ids, ['partner', 'id'], context=context):            
    #         res[item['id']] = uid == item['partner'][0]


    # def _search_uid_ok(self, cr, uid, obj, name, args, context=None):
    #     context = context or {}
    #     ids = self.search(cr, uid, [], context=context)
    #     items = self.read(cr, uid, ids, ['uid_ok'], context=context)
    #     res = []
    #     for item in items:
    #         if condition(args[0][1], item['uid_ok'], args[0][2]):
    #             res.append(item['id'])
    #     return [('id', 'in', res)] 



    time_flight_range1_plan = fields.Float(compute=_time_flight_range1_plan,store=False, digits=(16, 2))
    time_flight_range2_plan = fields.Float(compute=_time_flight_range2_plan,store=False, digits=(16, 2))
    time_flight_range3_plan = fields.Float(compute=_time_flight_range3_plan,store=False, digits=(16, 2))
    valid_time_flight_range1_plan = fields.Char(compute=_valid_time_flight_range1_plan,store=False)
    valid_time_flight_range2_plan = fields.Char(compute=_valid_time_flight_range2_plan,store=False)
    valid_time_flight_range3_plan = fields.Char(compute=_valid_time_flight_range3_plan,store=False)
    dias_tabajados_mes = fields.Integer(compute=_dias_tabajados_mes,store=False)
    dias_programados_mes = fields.Integer(compute=_dias_programados_mes,store=False)
    dias_trab_ano = fields.Integer(compute=_dias_trab_ano,store=False)
    dias_programados_ano = fields.Integer(compute=_dias_programados_ano,store=False)
    # uid_ok = fields.Boolean(compute=_uid_ok,store=False, search=_search_uid_ok)
