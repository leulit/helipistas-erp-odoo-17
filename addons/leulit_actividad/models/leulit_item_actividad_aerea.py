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



class ItemActividadAerea(models.Model):
    _name = "leulit.item_actividad_aerea"
    _description = "Item Actividad Aerea"
    _order = 'fecha DESC, inicio ASC'

    value_delta_pre = 0.75
    coeficiente_mayoracion = 1.5

    _tiempo_maximo_vuelo = {
        'AOC'               : 3.0,
        'Trabajo Aereo'     : 3.0,
        'LCI'               : 3.0,
        'Escuela'           : 3
    }
    _tiempo_maximo_vuelo_default = 3


    _tiempo_descanso_entre = {
        'AOC'               : 1,
        'Trabajo Aereo'     : 1,
        'LCI'               : 1,
        'Escuela'           : 1
    }
    _tiempo_descanso_entre_default = 1

    _tiempo_minimo_descanso = 0.16

    _max_horas_28d = 100
    _max_horas_12m = 900
    _max_horas_3p28d = 270

    _descanso_minimo = 10.5
    _descanso_parcial_min = 3
    _descanso_parcial_max = 4



    def getMinRestMin(self):
        return self._descanso_minimo * 60

    @api.depends('tiempo','coe_mayoracion','delta_pre','write_date')
    def _tiempo_calc(self):       
        for item in self:           
            valor = (item.tiempo*item.coe_mayoracion)+item.delta_pre
            _logger.error("fecha: %r tiempo: %r coe_mayoracion: %s, delta_pre: %r", item.fecha, item.tiempo, item.coe_mayoracion, item.delta_pre) 
            item.tiempo_calc = valor

    @api.depends('inicio','delta_pre','write_date')
    def _inicio_calc(self):       
        for item in self:            
            item.inicio_calc = item.inicio - item.delta_pre

    @api.depends('fecha','inicio','delta_pre','write_date')
    def _fecha_inicio_calc(self):       
        for item in self:            
            date2 = utilitylib.leulit_float_time_to_str( item.inicio_calc )
            date1 = item.fecha.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            item.fecha_inicio_calc = datetime.strptime(tira,"%Y-%m-%d %H:%M")

    @api.depends('fecha','inicio','write_date')
    def _fecha_inicio(self):       
        for item in self:            
            date2 = utilitylib.leulit_float_time_to_str( item.inicio )
            date1 = item.fecha.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            item.fecha_inicio = datetime.strptime(tira,"%Y-%m-%d %H:%M")

    @api.depends('fecha','fin','write_date')
    def _fecha_fin(self):       
        for item in self:            
            date2 = utilitylib.leulit_float_time_to_str( item.fin )
            date1 = item.fecha.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            item.fecha_fin = datetime.strptime(tira,"%Y-%m-%d %H:%M")


    
    fecha = fields.Date('Fecha', index=True)
    fecha_inicio = fields.Datetime(string="Fecha inicio",compute=_fecha_inicio, store=True)
    fecha_fin = fields.Datetime(string="Fecha fin",compute=_fecha_fin, store=True)
    fecha_inicio_calc = fields.Datetime(string="Fecha inicio calculado",compute=_fecha_inicio_calc, store=True)

    idmodelo = fields.Integer('idmodelo', index=True)
    modelo = fields.Char('Modelo', index=True)
    inicio = fields.Float('Inicio actividad', digits=(16, 2))
    fin = fields.Float('Fin actividad', digits=(16, 2))    
    horallegada = fields.Float('Hora llegada', digits=(16, 2))
    delta_pre = fields.Float('Delta previo', digits=(16, 2))
    delta_pos = fields.Float('Delta post', digits=(16, 2))

    inicio_calc = fields.Float(string="Incio calculado",compute=_inicio_calc,  store=True)
    tiempo_calc = fields.Float(string="Tiempo calculado",compute=_tiempo_calc, store=True)
    tiempo = fields.Float("Tiempo actividad", digits=(16, 2))
    airtime = fields.Float("Airtime", digits=(16, 2))
    prevista = fields.Boolean('Prevista')
    escuela = fields.Boolean('Escuela')
    ato = fields.Boolean('ATO')
    coe_mayoracion = fields.Float('Coeficiente mayoración')
    partner = fields.Many2one('res.partner', 'Empleado Helipistas', ondelete='restrict', index=True)
    rol = fields.Char('Rol empleado')
    descripcion = fields.Char('Descripción')
    tipo_actividad = fields.Char('Tipo actividad')
    actividad_aerea = fields.Many2one(comodel_name='leulit.actividad_aerea', string='Actividad aerea')
    valid_flight_time = fields.Char('T.V. Valido')
    prevista = fields.Boolean('Prevista')


    def getValidFlightTime(self):
        self.ensure_one()
        valor = "N.A."

        if self.tipo_actividad and self.tipo_actividad in self._tiempo_maximo_vuelo:
            valor = "red" if self.airtime > self._tiempo_maximo_vuelo[self.tipo_actividad] else "green"
        else:
            valor = "red" if self.airtime > self._tiempo_maximo_vuelo_default else "green"
        return valor


    def getVuelosByDatesAndPartner(self, fecha_ini, fecha_fin, partner_id):
        vuelos = self.search([('fecha','>=',fecha_ini),('fecha','<=',fecha_fin),('partner','=',partner_id),('modelo','=','leulit.vuelo'),('prevista','=',False)])
        return vuelos


    def deletePrevistasAnt( self, fecha, partner ):
        items = self.search( [('fecha','<=',fecha), ('partner','=',partner), ('prevista','=',True)] )
        items.unlink()



    def getCoeficienteMayoracion( self, fecha_fin, partner, inicio ):
        '''
        La instrucción en vuelo o simulador, siempre que preceda a un vuelo, tendrá un coeficiente de mayoración -salvo en Escuelas- de 1,5. 
        '''
        rows = self.search([
            ('fecha_inicio','>=', fecha_fin),
            ('partner', '=', partner),
            ('modelo','=','leulit.vuelo'),            
            '''
            ('escuela','=',True),            
            ('ato','=',False),            
            '''
        ])
        return self.coeficiente_mayoracion if  len(rows) > 0 else 0


    def getPreviousItems( self, fecha_inicio, idmodelo, modelo, partner):
        items = self.search([
            ('partner', '=', partner), 
            ('fecha_fin', '<=', fecha_inicio),
            ('idmodelo', '!=', idmodelo),
            ('modelo', '!=', modelo),
        ])        
        return items
        

    def setDeltaPreZero( self, fecha, idmodelo, modelo, partner):
        self.search([
            ('partner', '=', partner), 
            ('fecha', '=', fecha),
            ('idmodelo', '!=', idmodelo),
            ('modelo', '!=', modelo),
        ]).write({'delta_pre':0})


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

