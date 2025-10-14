# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
import threading
from odoo.addons.leulit import utilitylib
from dateutil.relativedelta import relativedelta
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class leulit_actividad_16bravo(models.Model):
    _name = "leulit.actividad_16bravo"
    _description = "leulit_actividad_16bravo"
    _order = "fecha desc, inicio asc, partner"


    _str_time_flight_range1 = "28d"
    _str_time_flight_range2 = "12m"
    _str_time_flight_range3 = "3*28d"

    @api.depends('tiempo','coe_mayoracion','delta_pre')
    def _tiempo_calc(self):       
        valor = False    
        for item in self:            
            item.tiempo_calc = (item.tiempo*item.coe_mayoracion)+item.delta_pre


    fecha = fields.Date('Fecha', index=True)
    partner = fields.Many2one('res.partner', 'Partner', ondelete='restrict', index=True)
    inicio = fields.Float('Inicio actividad', digits=(16, 2))
    fin = fields.Float('Fin actividad', digits=(16, 2))
    tiempo = fields.Float("Tiempo", digits=(16, 2))
    tiempo_calc = fields.Float(string="Tiempo calculado",compute=_tiempo_calc, digits=(16, 2), store=True)
    tiempo_vuelo = fields.Float("Tiempo Vuelo", digits=(16, 2))
    prevista = fields.Boolean('Prevista')
    actividades = fields.One2many('leulit.actividad_base', 'actividad_16bravo_id', 'Actividades')
    #actividad_16bravo_dia_id = fields.One2many('leulit.actividad_16bravo_dia', 'actividad_16bravo_id', 'Actividad 16bravo día')
    actividad_16bravo_dia_id = fields.Many2one('leulit.actividad_16bravo_dia', 'Actividad 16bravo día')


    tiempo_aa = fields.Float(related='actividad_16bravo_dia_id.tiempo',string='Tiempo actividad aérea', readonly=True)
    tiempo_a = fields.Float(related='actividad_16bravo_dia_id.tiempo_act', string="Tiempo actividad", readonly=True)
    valid_activity_time = fields.Char(related='actividad_16bravo_dia_id.valid_activity_time', string="Tiempo actividad válido", readonly=True)
    max_duracion = fields.Float(related='actividad_16bravo_dia_id.max_duracion', string="Tiempo máximo AA", readonly=True)
    tiempo_desc_parcial = fields.Float(related='actividad_16bravo_dia_id.tiempo_desc_parcial', string="Tiempo descanso parcial", readonly=True)
    tiempo_amplia = fields.Float(related='actividad_16bravo_dia_id.tiempo_amplia', string="Tiempo ampliación por descanso", readonly=True)

    idmodelo = fields.Integer('idmodelo', index=1)
    modelo = fields.Char('Modelo', index=1)
    escuela = fields.Boolean('Escuela')
    ato = fields.Boolean('ATO')
    coe_mayoracion = fields.Float('Coeficiente mayoración')
    delta_pre = fields.Float('Tiempo previo')
    tipo_actividad = fields.Char('Tipo actividad')
    



    @api.model
    def upd_datos_scheduled_action(self, fechaini=None, fechafin=None):
        _logger.error("upd_datos_scheduled_action ")        
        _logger.error("fecha ini = %r",fechaini)
        _logger.error("fecha fin = %r",fechafin)
        threaded_calculation = threading.Thread(target=self.run_upd_datos_scheduled_action, args=([fechaini, fechafin]))
        _logger.error("upd_datos_scheduled_action start thread")
        threaded_calculation.start()        
        _logger.error("upd_datos_scheduled_action end thread")
        return {}



    @api.model
    def procesarVuelos(self, fechaini, fechafin, context):
        vuelos = self.env['leulit.vuelo'].search([('fechavuelo','>=',fechaini),('fechavuelo','<=',fechafin),('estado','in',['postvuelo','cerrado'])])
        for vuelo in vuelos:
            _logger.error("--> vuelo = %r",vuelo)
            vuelo.updDataActividad()

    @api.model
    def run_upd_datos_scheduled_action(self, fechaini=None, fechafin=None):
        _logger.error("run_upd_datos_scheduled_action ")        
        _logger.error("fecha ini = %r",fechaini)
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            self.env.cr.autocommit(True) 
            context = dict(self._context)
            self.procesarVuelos(fechaini, fechafin, context)
            _logger.error("fecha fin = %r",fechafin)
