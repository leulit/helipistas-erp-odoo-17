from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional
from dateutil.relativedelta import relativedelta
from odoo.addons.leulit import utilitylib
from datetime import datetime
from . import actividad

import logging
_logger = logging.getLogger(__name__)


class ActividadAereaChainRequest():
    _name = "ActividadAereaChainRequest"
    
    error = None
    errorCode = "000"
    errormsg = ""

    errorCode_NO_DESCANSO = "001"
    errorCode_SOLAPAMIENTO = "002"
    errorCode_DESCANSO_MINIMO_NOVALIDO = "003"

    fecha = None    
    inicio = 0.0
    horallegada = 0.0
    partner = 0
    prevista = False
    delta_pre = 0.0   
    modelo = ''
    idmodelo = 0
    tiempo = 0.0
    airtime = 0.0
    tiempoaa = 0.0
    actividad_aerea = False
    prevista = False
    rol = ''
    descripcion = ''
    tipo_actividad = ''

    env = None
    _time_pre_vuelo = 0.75
    escuela = False
    ato = False
    coe_mayoracion = 1
    time_flight_range1 = 0.0
    time_flight_range2 = 0.0
    time_flight_range3 = 0.0
    descanso_prev = 0.0
    dias_trabajados_mes = 0
    actividad_aerea_id = 0
    item_actividad_aerea_id = 0

    @property
    def iniciocalc(self):
        return round(round(float(self.inicio),2) - round(float(self.delta_pre),2),2)

    @property
    def fin(self):
        return round(round(float(self.inicio),2) + round(float(self.tiempo),2),2)


    @property
    def fecha_ini(self):
        date2 = utilitylib.leulit_float_time_to_str( self.iniciocalc )
        date1 = self.fecha.strftime("%Y-%m-%d")
        tira =  date1+" "+date2
        valor = datetime.strptime(tira,"%Y-%m-%d %H:%M")
        return valor

    @property
    def fecha_fin(self):
        date2 = utilitylib.leulit_float_time_to_str( self.fin )
        date1 = self.fecha.strftime("%Y-%m-%d")
        tira =  date1+" "+date2
        valor = datetime.strptime(tira,"%Y-%m-%d %H:%M")
        return valor

    @property
    def tiempocalc(self):
        return round(round(float(self.tiempo),2) * round(float(self.coe_mayoracion),2),2)

    @property
    def descanso_minimo_minutes(self):
        return round(((10*60)+30),2)


class DeleteData(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        request.env['leulit.actividad_aerea'].search([('fecha','=',request.fecha),('partner','=',request.partner),]).unlink()
        request.env['leulit.item_actividad_aerea'].search([('fecha','=',request.fecha),('partner','=',request.partner)]).unlink()
        request.env.cr.commit()
        return super().handle(request)


class CheckOverlap(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-AA--> CheckOverlap")
        if not request.error:
            o_iaa = request.env['leulit.item_actividad_aerea']
            result = o_iaa.check_overlap(request.item_actividad_aerea_id, request.fecha, request.fecha_ini, request.fecha_fin, request.partner)
        return super().handle(request)


class DeleteItemsActividadAereaPrevistaPrevia(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-AA--> DeleteItemsActividadAereaPrevistaPrevia")
        if not request.error:
            o_iaa = request.env['leulit.item_actividad_aerea']
            o_iaa.deletePrevistasAnt( request.fecha, request.partner )
            request.env.cr.commit()
        return super().handle(request)


class ActividadAereaPreVueloHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        if not request.error:
            o_iaa = request.env['leulit.item_actividad_aerea']
            for item in o_iaa.search([('fecha','=',request.fecha),('partner','=',request.partner),('prevista','=',False)],order="fecha ASC, inicio ASC"):
                if item.modelo == 'leulit.vuelo':
                    nitems = o_iaa.search_count([('fecha','=',item.fecha),('fin', '<=', item.inicio),('partner','=',item.partner.id),('prevista','=',False),('modelo','=','leulit.vuelo')])
                    deltapre = o_iaa.value_delta_pre if nitems == 0 else 0
                else:
                    deltapre = 0
                item.delta_pre = deltapre
            request.env.cr.commit()
        return super().handle(request)


class CheckDescanso(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-AA--> CheckDescanso")
        if not request.error:
            enoughRest = 0
            o_aa = request.env['leulit.actividad_aerea']
            o_iaa = request.env['leulit.item_actividad_aerea']

            items_aaAnt = o_aa.search([('fecha','<',request.fecha),('partner','=',request.partner)], limit=1, order='fecha DESC')
            items_aa = o_aa.search([('fecha','=',request.fecha),('partner','=',request.partner)], limit=1, order='fecha DESC')

            if items_aaAnt and items_aaAnt.id:
                enoughRest = items_aa.enoughRestMin( items_aaAnt.partner.id, items_aaAnt.fecha_fin)

        return super().handle(request)


class ParteEscuelaHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-AA--> ParteEscuelaHandler %r", request.fecha)
        if not request.error:
            o_ipe = request.env['leulit.parte_escuela']
            o_iaa = request.env['leulit.item_actividad_aerea']
            for item in o_ipe.search([('fecha','=',request.fecha),('estado','=','cerrado'),('vuelo_id','=',False)],order="fecha ASC, hora_start ASC"):
                if item.sudo().profesor.partner_id.id == request.partner:
                    iaa_domain_search = [('modelo','=','leulit.vuelo'),('fecha','=',request.fecha),('partner','=',request.partner),('prevista','=',False),('inicio','>=',item.hora_end)]
                    nitems = o_iaa.search_count(iaa_domain_search)
                    _logger.error("-AA--> ParteEscuelaHandler nitems = %r", nitems)
                    if nitems > 0:
                        datos = {
                            'fecha' : request.fecha,
                            'prevista' : request.prevista,
                            'partner' : request.partner,
                            'inicio' : item.hora_start,
                            'fin' : item.hora_end,
                            'tiempo' : item.tiempo,
                            'idmodelo' : item.id,
                            'modelo' : 'leulit.parte_escuela',
                            'coe_mayoracion' : 1,
                            'escuela' : False,
                            'ato' : True,
                            'descripcion' : item.name,
                            'rol' : 'profesor',
                        }
                        o_itemIaa = o_iaa.search([
                                ('idmodelo','=',item.id),
                                ('modelo','=','leulit.parte_escuela'),
                                ('partner','=',request.partner),
                            ], order="fecha ASC, inicio ASC")
                        if o_itemIaa:
                            o_itemIaa.write(datos)
                        else:
                            o_itemIaa = o_iaa.sudo().create(datos)
                        # PROCEDEMOS A RECALCULAR EL DELTA PRE SI EL TIEMPO ENTRE CLASE Y VUELO ES MENOR A 45 MINUTOS MANTENIENDO DELTA PRE COMO EL TIEMPO ENTRE AMBOS EVENTOS
                        for item2 in o_iaa.search(iaa_domain_search,order="fecha ASC, inicio ASC", limit=1):
                            if item2.delta_pre > 0:
                                if item2.inicio - item.hora_end < o_iaa.value_delta_pre:
                                    item2.delta_pre = item2.inicio - item.hora_end 

        request.env.cr.commit()
        return super().handle(request)


class ItemActividadAreaHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-AA--> ItemActividadAreaHandler")
        if not request.error:
            o_iaa = request.env['leulit.item_actividad_aerea']
            o_itemIaa = o_iaa.search([
                ('idmodelo','=',request.idmodelo),
                ('modelo','=',request.modelo),
                ('partner','=',request.partner),
            ], order="fecha ASC, inicio ASC")
            # SI LA ACTIVIDAD QUE SE ESTÁ PROCESANDO YA EXISTÍA PERO EN OTRA FECHA
            # ELIMINAMOS LA ACTIVIDAD ANTERIOR Y GENERAMOS LA NUEVA
            if o_itemIaa and o_itemIaa.fecha != request.fecha:
                o_itemIaa.unlink()
                o_itemIaa = None

            datos = {
                'fecha' : request.fecha,
                'prevista' : request.prevista,
                'partner' : request.partner,
                'inicio' : request.inicio,
                'horallegada' : request.horallegada,
                'fin' : request.fin,
                'tiempo' : request.tiempo,
                'airtime' : request.airtime,
                'tipo_actividad' : request.tipo_actividad,
                'idmodelo' : request.idmodelo,
                'modelo' : request.modelo,
                'coe_mayoracion' : request.coe_mayoracion,
                'escuela' : request.escuela,
                'ato' : request.ato,
                'descripcion' : request.descripcion,
                'rol' : request.rol,
            }
            if o_itemIaa:
                o_itemIaa.write(datos)
            else:
                o_itemIaa = o_iaa.sudo().create(datos)
            request.env.cr.commit()
            request.item_actividad_aerea_id = o_itemIaa.id
        return super().handle(request)


class ItemActividadAreaValidFlightTimeHandler(actividad.AbstractHandler):

     def handle(self, request: Any) -> Any:
        _logger.error("-AA--> ItemActividadAreaValidFlightTimeHandler")
        if not request.error:           
            o_iaa = request.env['leulit.item_actividad_aerea']
            for item in o_iaa.search([('idmodelo','=',request.idmodelo), ('modelo','=',request.modelo), ('partner','=',request.partner)], order="fecha ASC, inicio ASC"):
                valor = item.getValidFlightTime()
                item.valid_flight_time = valor
            request.env.cr.commit()
        return super().handle(request)


class CoeficienteMayoracionHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        if not request.error:
            _logger.error("-AA--> CoeficienteMayoracionHandler")
            o_iaa = request.env['leulit.item_actividad_aerea']
            for item in o_iaa.search([('fecha','=',request.fecha),('partner','=',request.partner),('prevista','=',False)],order="fecha ASC, inicio ASC"):
                nitems = o_iaa.search_count([('modelo','=','leulit.vuelo'),('fecha','=',item.fecha),('inicio', '>=', item.fin),('partner','=',item.partner.id),('prevista','=',False)])
                coe_mayoracion = 1.5 if ((nitems >0) and item.escuela and (not item.ato)) else 1
                item.coe_mayoracion = coe_mayoracion
            request.env.cr.commit()
        return super().handle(request)


class CalcularActividadAerea(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-AA--> CalcularActividadAerea")
        if not request.error:
            o_iaa = request.env['leulit.item_actividad_aerea']
            o_aa = request.env['leulit.actividad_aerea']    
            items_aa = o_iaa.search([('fecha','=',request.fecha),('partner','=',request.partner)], order="fecha ASC, inicio ASC")
            tiempoaa = 0.0
            max_duracion = 0.0
            tiempo_desc_parcial = 0.0
            tiempo_amplia = 0.0
            inicioitems = 1111.0
            finitems = 0.0
            incremento = 0.0
            airtime = 0.0
            tiempo_vuelo = 0.0
            for index,itemaa in enumerate(items_aa):
                airtime += itemaa.airtime
                #tiempo = itemaa.tiempo_calc if itemaa.tiempo_calc else 0
                #tiempoaa = tiempoaa + tiempo
                tiempo_vuelo += itemaa.tiempo

                #cálculo tiempo máxima de actividad
                if itemaa.tipo_actividad in o_aa.tiempo_maximo_tipo_actividad:
                    max_duracion = max(o_aa.tiempo_maximo_tipo_actividad[ itemaa.tipo_actividad ], max_duracion)
                else:
                    if itemaa.escuela:
                        if itemaa.ato:
                            max_duracion = o_aa.tiempo_maximo_tipo_actividad['Escuela-ATO']
                        else:
                            max_duracion = o_aa.tiempo_maximo_tipo_actividad['Escuela-noATO']
                    else:
                        max_duracion = o_aa.default_tiempo_maximo_tipo_actividad
                #cálculos descanso parcial
                if (index > 0):
                    itemaaAnt = items_aa[index-1]
                    intervalo = round(float(itemaa.inicio_calc),2) - round(float(itemaaAnt.fin),2)
                    if intervalo >= o_aa.descanso_parcial_min and intervalo <= o_aa.descanso_parcial_max:
                        if intervalo > o_aa.descanso_parcial_max:
                            intervalo = 8.0
                        incremento = round((intervalo / 2.0),2)
                    
                        tiempo_desc_parcial = tiempo_desc_parcial + intervalo
                        tiempo_amplia = tiempo_amplia + incremento

                inicioitems = min(inicioitems, itemaa.inicio_calc)
                finitems = max(finitems, itemaa.fin)


            ## CALCULAR TIEMPO ACTIVIDAD AREA TENIENDO EN CUENTA QUE PUEDEN HABER INTÉRVALOS DE TIEMPO QUE SE SOLAPEN
            # intervals = []
            # for itemaa in items_aa:
            #     inicio = itemaa.inicio_calc
            #     fin = itemaa.fin

            #     intervals.append( [ inicio, fin ] )
            # if len(intervals) > 1:
            #     intervals.sort(key=lambda x:x[0])
            #     intervals = utilitylib.merge_intervals(intervals)
            # # _logger.error("--> employee %r intervals 2 = %r fecha = %r",employee_id, intervals, fecha)
            # total = 0
            # if intervals:
            #     for item in intervals:
            #         total += item[1] - item[0]
            # _logger.error("--> employee %r total = %r",employee_id, total)
            # tiempoaa  = total                

            itemAA = o_aa.search([('fecha','=',request.fecha),('partner','=',request.partner)])
            nItemsAAATO = o_iaa.search_count([('fecha','=',request.fecha),('partner','=',request.partner),('ato','=',True)])
            datos = {
                'fecha' : request.fecha,
                'partner' : request.partner,
                'inicio' : inicioitems,
                'fin' : finitems,
                'tiempo_amplia' : tiempo_amplia if itemAA.aplica_desc_parcial else 0.0,
                'airtime' : airtime,
                'tiempo_desc_parcial' : tiempo_desc_parcial if itemAA.aplica_desc_parcial else 0.0,
                'max_duracion' : max_duracion + tiempo_amplia if itemAA.aplica_desc_parcial else max_duracion,
                'tiempo' : finitems - inicioitems,
                'tiempo_vuelo' : tiempo_vuelo,
                #SI EL DÍA INCLUYE UNA ACTIVIDAD ATO SE CONSIDERA QUE AL ACTIVIDAD AÉREA DE ESE DÍA ES ATO
                'ato' : True if nItemsAAATO > 0 else False,
                'valid_activity_time' : "green" if round(float(tiempoaa),2) <= round(float(max_duracion),2) else "red"
            }
            if itemAA and itemAA.id:
                itemAA.sudo().write(datos)
            else:
                itemAA = o_aa.sudo().create(datos)
            if len(items_aa.ids) > 0:
                items_aa.sudo().write({'actividad_aerea':itemAA.id})
                
            request.actividad_aerea_id = itemAA.id
            request.env.cr.commit()
        return super().handle(request)



class UpdateATOActitivdadAreaHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-AA--> UpdateATOActitivdadAreaHandler")
        if not request.error:
            o_iaa = request.env['leulit.item_actividad_aerea']
            o_aa = request.env['leulit.actividad_aerea']  
            nItemsAAATO = o_iaa.search_count([('fecha','=',request.fecha),('partner','=',request.partner),('ato','=',True)])
            o_aa.search([('fecha','=',request.fecha),('partner','=',request.partner)]).write({'ato':True if nItemsAAATO > 0 else False})
            request.env.cr.commit()
        return super().handle(request)


class TimeRangeHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        if not request.error:
            _logger.error("-AA--> TimeRangeHandler")        
            _logger.error("-AA--> request.fecha = %r",request.fecha)        
            sql = """
                UPDATE 
                    leulit_actividad_aerea
                SET
                    time_flight_range1 = subquery.time_flight_range1,
                    time_flight_range2 = subquery.time_flight_range2,
                    time_flight_range3 = subquery.time_flight_range3                
                FROM 
                    (	
                        select * from leulit_time_flight_range
                        where fecha >= '{0}'::DATE and partner = {1}
                    ) AS subquery
                WHERE
                    leulit_actividad_aerea.id = subquery.actividad_aerea
            """.format( request.fecha.strftime("%Y-%m-%d"), request.partner )
            #_logger.error("-AA--> TimeRangeHandler sql  = %r",sql)        
            request.env.cr.execute(sql)
            request.env.cr.commit()
        return super().handle(request)


class DiasTrabajadosMesHandler(actividad.AbstractHandler):

    def handle(self, request: Any) -> Any:
        if not request.error:
            _logger.error("-AA--> DiasTrabajadosMesHandler")        
            fechasMonth = utilitylib.startEndMonth( objfecha = request.fecha )
            for item in request.env['leulit.actividad_aerea'].search([('fecha','>=',request.fecha), ('fecha','<=',fechasMonth['endmonth']), ('partner','=',request.partner)]):
                numitems = request.env['leulit.actividad_aerea'].search_count([('fecha','>=',fechasMonth['startmonth']), ('fecha','<=',item.fecha), ('partner','=',request.partner)])
                item.dias_trabajados_mes = numitems
            request.env.cr.commit()
            request.dias_trabajados_mes = numitems          
        return super().handle(request)