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

class leulit_actividad_16bravo_dia(models.Model):
    _name = "leulit.actividad_16bravo_dia"
    _description = "leulit_actividad_16bravo_dia"
    _order = "fecha desc, inicio asc, partner"

    def detalle(self):
        return True
    #TODO def detalle(self, ids, context=None):
    #     view_ref = self.pool.get('ir.model.data')._xmlid_to_res_model_res_id('leulit_actividad'. 'leulit_20201211_1750_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     itemIds = self.pool['actividad_base'].search([('actividad_16bravo_dia_id','=',ids)])
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Detalle actividad aérea día',
    #         'res_model': 'actividad_base',
    #         'view_type': 'form',
    #         'view_mode': 'tree',
    #         'view_id': view_id,
    #         'res_id': itemIds,
    #         'context': context,
    #         'initial_mode': 'view',
    #         'target': 'new',
    #         'domain': [('actividad_16bravo_dia_id','in',ids)],
    #         'flags' : {'form': {'action_buttons': False}}
    #     }

    def detalle_av(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_actividad.leulit_20201211_1750_tree')
        view_id = view_ref and view_ref[1] or False
        itemIds = []
        for item in self:
            itemIds = self.env['leulit.actividad_base'].search([('actividad_16bravo_dia_id','=',item.actividad_16bravo_dia_id.id),('rol','!=','operador')])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actividad vuelo {0}'.format(item['fecha']),
            'res_model': 'leulit.actividad_base',
            'view_mode': 'tree',
            'view_id': view_id,
            'res_id': itemIds,
            'domain': [('actividad_16bravo_dia_id','=',item.actividad_16bravo_dia_id.id),('rol','!=','operador')],
        }

    def detalle_28d(self):
        return True
    #     view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id( 'leulit_actividad'. 'leulit_202012142340_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     item = self.read(cr, uid, ids, [])[0]
    #     fecha_ini = self.getFechaIniPeriodo(self._str_time_flight_range1, item['fecha'])
    #     itemIds = self.pool['actividad_16bravo'].search(cr, uid, [('fecha','>=',fecha_ini),('fecha','<=',item['fecha']),('user_id','=',item['user_id'][0])])
    #     titulo = 'Actividad vuelo {0} a {1}'.format(self.str_date_format(cr, uid, fecha_ini), self.str_date_format(cr, uid, item['fecha']))
    #     return self._detalle(cr, uid, ids, itemIds, view_id, titulo, context)

    def detalle_12m(self):
        return True
    #     view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id( 'leulit_actividad'. 'leulit_202012142340_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     item = self.read(cr, uid, ids, [])[0]
    #     fecha_ini = self.getFechaIniPeriodo(self._str_time_flight_range2, item['fecha'])
    #     itemIds = self.pool['actividad_16bravo'].search(cr, uid, [('fecha','>=',fecha_ini),('fecha','<=',item['fecha']),('user_id','=',item['user_id'][0])])
    #     titulo = 'Actividad vuelo {0} a {1}'.format(self.str_date_format(cr, uid, fecha_ini), self.str_date_format(cr, uid, item['fecha']))
    #     return self._detalle(cr, uid, ids, itemIds, view_id, titulo, context)

    def detalle_3m(self):
        return True
    #     view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id( 'leulit_actividad'. 'leulit_202012142340_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     item = self.read(cr, uid, ids, [])[0]
    #     fecha_ini = self.getFechaIniPeriodo(self._str_time_flight_range3, item['fecha'])
    #     itemIds = self.pool['actividad_16bravo'].search(cr, uid, [('fecha','>=',fecha_ini),('fecha','<=',item['fecha']),('user_id','=',item['user_id'][0])])
    #     titulo = 'Actividad vuelo {0} a {1}'.format(self.str_date_format(cr, uid, fecha_ini), self.str_date_format(cr, uid, item['fecha']))
    #     return self._detalle(cr, uid, ids, itemIds, view_id, titulo, context)


    def detalle_diasmes(self):
        return True
    #     view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id( 'leulit_actividad'. 'leulit_202012142340_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     item = self.read(cr, uid, ids, [])[0]
    #     fecha_ini = utilitylib.startMonth( item['fecha'], return_str = True )
    #     itemIds = self.pool['actividad_16bravo'].search(cr, uid, [('fecha','>=',fecha_ini),('fecha','<=',item['fecha']),('user_id','=',item['user_id'][0])])
    #     titulo = 'Días trabajados mes {0}'.format(self.str_date_format(cr, uid, fecha_ini, formatDestino="%m-%Y"))
    #     return self._detalle(cr, uid, ids, itemIds, view_id, titulo, context)




    def _has_ato(self):       
        valor = False    
        for item in self:            
            for actividad in item.actividades_16bravo:
                if actividad.ato and actividad.escuela:
                    valor = True
            item.has_ato = valor


    def _tiempo_aa(self):       
        for item in self:            
            tiempo = 0.0
            _logger.error("-AA--> _tiempo_aa = %r",item)
            for actividad in item.actividades_16bravo:
                _logger.error("-AA--> actividad = %r",actividad)
                _logger.error("-AA--> actividad.tiempo = %r",actividad.tiempo)
                tiempo = tiempo + actividad.tiempo
            _logger.error("-AA--> tiempo = %r",tiempo)
            item.tiempo_aa = tiempo


    def _time_flight_range1(self):
        for item in self:
            piloto = self.env['leulit.piloto'].search([('partner_id', '=', item.partner.id)])
            sql = '''
                SELECT 
			            coalesce(SUM(leulit_vuelo.airtime),0)
		            FROM 
			            leulit_vuelo
		            WHERE 
			            leulit_vuelo.fechavuelo >= ('{0}'::DATE - (INTERVAL '28 DAY'))
		            AND
			            leulit_vuelo.fechavuelo <= '{0}'::DATE
		            AND
			            (
                            leulit_vuelo.piloto_id = {1}
                            OR
                            leulit_vuelo.piloto_supervisor_id = {1}
                            OR
                            leulit_vuelo.piloto_supervisor_id = {1}
                        )
            '''.format(item.fecha, item.partner.id)
            row = utilitylib.runQueryReturnOne(self._cr, sql)        
            item.time_flight_range1_plan = row['total']

    
    fecha = fields.Date('Fecha', index=True)
    fecha_inicio = fields.Datetime('Fecha inico')
    fecha_fin = fields.Datetime('Fecha fin')
    prevista = fields.Boolean('Prevista')
    partner = fields.Many2one('res.partner', 'Partner', ondelete='restrict', index=True)
    inicio = fields.Float('Inicio actividad', digits=(16, 2))
    fin = fields.Float('Fin actividad', digits=(16, 2))
    descanso_prev = fields.Float("Descanso previo", digits=(16, 2))
    valid_descanso_prev = fields.Char(string='Descanso previo válido')
    tiempo = fields.Float("Tiempo actividad aérea", digits=(16, 2))
    tiempo_act = fields.Float("Tiempo actividad", digits_compute=dp.get_precision('dp_actividad'))
    tiempo_desc_parcial = fields.Float("Tiempo descanso_parcial actividad aérea", digits_compute=dp.get_precision('dp_actividad'))
    tiempo_amplia = fields.Float("Tiempo amplicación actividad aérea", digits=(16, 2))
    tiempo_aa = fields.Float(compute=_tiempo_aa, store=False, string="Tiempo Act. Aérea")  

    max_duracion = fields.Float("Duración máxima actividad", digits=(16, 2))
    actividades_16bravo = fields.One2many('leulit.actividad_16bravo', 'actividad_16bravo_dia_id', 'Actividad 16bravo día')
    tiempo_vuelo = fields.Float("Tiempo Vuelo", digits=(16, 2))

    dias_trabajados_mes = fields.Integer('Dias Tr. mes')
    valid_dias_trabajados_mes = fields.Char('Días trabajados mes ok')

    valid_activity_time = fields.Char(string='Tiempo actividad aérea valido')
    has_ato = fields.Boolean(compute=_has_ato, store=False, string="ATO")    

    #time_flight_range1 = fields.Float(string="TV 28d",type="float", digits=(16, 2))    
    time_flight_range1 = fields.Float(compute=_time_flight_range1,string="TV 28d",store=False, digits=(16, 2))
    valid_time_flight_range1 = fields.Char('28 d. ok')
    time_flight_range2 = fields.Float(string="TV 12 m.",type="float", digits=(16, 2))
    valid_time_flight_range2 = fields.Char('12 m. ok')
    time_flight_range3 = fields.Float(string="TV 3 m.",type="float", digits=(16, 2))
    valid_time_flight_range3 = fields.Char('3 m. ok')    

    dias_tabajados_mes = fields.Integer('Dias Tr. mes')
    valid_dias_tabajados_mes = fields.Char('Días trabajados mes ok')




