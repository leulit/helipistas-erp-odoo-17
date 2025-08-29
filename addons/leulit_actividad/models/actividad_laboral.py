from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional
from odoo.addons.leulit import utilitylib

from . import actividad

import logging
_logger = logging.getLogger(__name__)


class ActividadLaboralChainRequest():
    errorCode_SOLAPAMIENTO = "001"

    _name = "ActividadLaboralChainRequest"
    error = None
    errorCode = "000"
    errormsg = ""

    fecha = None    
    inicio = 0.0
    fin = 0.0
    partner = 0
    prevista = False
    delta_pre = 0.0   
    tiempo = 0.0     
    modelo = ''
    idmodelo = 0
    tiempo = 0.0
    actividad_aerea = False
    prevista = False
    rol = ''
    descripcion = ''
    tipo_actividad = ''

    actividad_base_dia_id = None
    actividad_base_id = None
    env = None
    _time_pre_vuelo = 0.75

    @property
    def iniciocalc(self):
        return round(round(float(self.inicio),2) - round(float(self.delta_pre),2),2)

    @property
    def tiempoLaboralActividad(self):
        return round(round(float(self.fin),2) - round(float(self.iniciocalc),2),2)


class SolapamientoHandler(actividad.AbstractHandler):
    def handle(self, request: Any) -> Any:
        _logger.error("---> handlerAL = SolapamientoHandler")
        if not request.error:
            o_ab = request.env['leulit.actividad_base']
            abds = o_ab.search([('partner', '=', request.partner), ('fecha','=',request.fecha), ('idmodelo','!=',request.idmodelo), ('modelo','!=',request.modelo)])            
            intervals = []
            for item in abds:
                intervals.add([item.inicio,item.fin])
            intervals.append([request.iniciocalc, request.fin])
            _logger.error("-AL--> SolapamientoHandler intervals = %r", intervals)        
            overlaped = utilitylib.getOverlapedIntervals(intervals)
            if len(overlaped) > 0:
                _logger.error("-AL--> SolapamientoHandler overlaped = %r",overlaped)        
                request.error = True
                request.errorCode = request.errorCode_SOLAPAMIENTO
                request.errormsg = "Existe solapamiento de la actividad en curso con otra actividad"
        _logger.error("-AL--> SolapamientoHandler create")
        return super().handle(request)


class ActividadBaseHandler(actividad.AbstractHandler):
    def handle(self, request: Any) -> Any:
        _logger.error("---> handlerAL = ActividadBaseHandler")
        if not request.error:
            o_ab = request.env['leulit.actividad_base']
            ab = o_ab.search([('modelo','=',request.modelo), ('idmodelo','=',request.idmodelo)])
            if ab:
                _logger.error("-AL--> ActividadBaseHandler write")
                _logger.error("-AL--> ActividadBaseHandler request = %r", request)
                _logger.error("-AL--> ActividadBaseHandler request.actividad_base_dia_id = %r", request.actividad_base_dia_id)
                #SI LA FECHA DE LA ACTIVIDAD A PROCESAR ES DIFERENTE DE LA FECHA ALMACENADA EN LA BASE DE DATOS
                #IMPLICA UN CAMBIO DE FECHA DE LA ACTIVIDAD CREADA ANTERIORMENT
                #POR LO TANTO DEBE ASIGNARSE A OTRA actividad_base_dia.
                #PARA SU POSTERIOR PROCESAMIENTO DE FORMA CORRECTA actividdad_base_dia_id SE IGUALA A none
                if ab.fecha != request.fecha:
                    request.actividad_base_dia_id = False
                datos = {
                    'fecha' : request.fecha,
                    'prevista' : request.prevista,
                    'partner' : request.partner,
                    'inicio' : request.iniciocalc,
                    'fin' : request.fin,
                    'delta_pre' : request.delta_pre,
                    'tiempo' : request.tiempo,
                    'actividad_aerea' : request.actividad_aerea,
                    'prevista' : request.prevista,
                    'rol' : request.rol,
                    'descripcion' : request.descripcion,
                    'tipo_actividad' : request.tipo_actividad,
                    'actividad_base_dia_id': request.actividad_base_dia_id
                }
                _logger.error("-AL--> ActividadBaseHandler datos = %r", datos)
                _logger.error("-AL--> ActividadBaseHandler ab = %r", ab)
                ab.write(datos)
            else:
                _logger.error("-AL--> ActividadBaseHandler create")
                ab = o_ab.create({
                    'fecha' : request.fecha,
                    'prevista' : request.prevista,
                    'partner' : request.partner,
                    'inicio' : request.iniciocalc,
                    'fin' : request.fin,
                    'idmodelo' : request.idmodelo,
                    'modelo' : request.modelo,
                    'delta_pre' : request.delta_pre,
                    'tiempo' : request.tiempo,
                    'actividad_aerea' : request.actividad_aerea,
                    'prevista' : request.prevista,
                    'rol' : request.rol,
                    'descripcion' : request.descripcion,
                    'tipo_actividad' : request.tipo_actividad,
                })
            #algoritmo
            _logger.error("-AL--> ActividadBaseHandler ab.id -> %r",ab.id)
            request.actividad_base_id = ab.id
            _logger.error("-AL--> ActividadBaseHandler")
        return super().handle(request)


class ActividadBaseDiaHandler(actividad.AbstractHandler):
    def handle(self, request: Any) -> Any:
        _logger.error("---> handlerAL = ActividadBaseDiaHandler")
        if not request.error:
            o_abd = request.env['leulit.actividad_base_dia']
            abd = o_abd.search([('partner', '=', request.partner), ('fecha','=',request.fecha)])
            if abd:
                _logger.error("-AL--> ActividadBaseDiaHandler write")
                inicio = min(request.iniciocalc, abd.inicio)
                fin = max(request.fin, abd.fin)
                abd.write({
                    'inicio' : inicio,
                    'fin' : fin
                })
            else:
                _logger.error("-AL--> ActividadBaseDiaHandler create")
                abd = o_abd.create({
                    'fecha' : request.fecha,
                    'prevista' : request.prevista,
                    'partner' : request.partner,
                    'inicio' : request.iniciocalc,
                    'fin' : request.fin
                })
            request.actividad_base_dia_id = abd.id

            #PROCEDEMOS A ACTUALIZAR EL id RELACION CON actividad_base

            abitems = request.env['leulit.actividad_base'].search([('partner', '=', request.partner), ('fecha','=',request.fecha)])
            _logger.error("-AL--> abitems = %r",abitems)
            _logger.error("-AL--> request.actividad_base_dia_id = %r",request.actividad_base_dia_id)
            abitems.write({
                'actividad_base_dia_id' : request.actividad_base_dia_id
            })
            _logger.error("-AL--> ActividadBaseDiaHandler")
            _logger.error("-AL--> ActividadBaseDiaHandler abc = %r", request.actividad_base_dia_id)
        return super().handle(request)


class LaboralPreVueloHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        if not request.error:
            o_abd = request.env["account.analytic.line"]
            numitems = o_abd.search([
                ('partner', '=', request.partner), 
                ('fecha','=',request.fecha),
                ('fin','<=',request.inicio),
                ('idmodelo','!=',request.idmodelo),
                ('modelo','!=',request.modelo),
            ], count=True)
            _logger.error("---> LaboralPreVueloHandler numitems = %r",numitems)     
            #si existe alguna actividad nterior al vuelo que se esta procesando no se añaden los 45 minutos
            if numitems > 0:
                request.delta_pre = 0
            else:
                request.delta_pre = request._time_pre_vuelo
            _logger.error("---> LaboralPreVueloHandler request.delta_pre = %r",request.delta_pre)     
        return super().handle(request)