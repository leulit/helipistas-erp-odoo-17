from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional
from dateutil.relativedelta import relativedelta
from odoo.addons.leulit import utilitylib
from datetime import datetime
from odoo.addons.leulit_operaciones import vuelo
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError

import logging
_logger = logging.getLogger(__name__)


class VueloChainToCerradoRequest():
    _name = "VueloChainToCerradoRequest"
    
    error = None
    errorCode = "000"
    errormsg = ""
    

    env = None
    vuelo_id = 0
    uid = 0
    tipo_helicoptero = ''


class ComprobacionPresupuestoHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionPresupuestoHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            
            if not vuelo.presupuesto_vuelo:
                raise UserError ('Este vuelo no puede pasar a cerrado. NO HA SELECCIONADO EL PRESUPUESTO')

            request.env.cr.commit()
        return super().handle(request)


class ComprobacionChecksHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionChecksHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)

            if not vuelo.checklist_postvuelo_realizado:
                raise UserError ('Este vuelo no puede pasar a cerrado. NO HA MARCADO LA INSPECCIÓN POSTVUELO CÓMO REALIZADA')

            request.env.cr.commit()
        return super().handle(request)


# class ComprobacionOtrosVuelosHandler(vuelo.AbstractHandler):

#     def handle(self, request: Any) -> Any:
#         _logger.error("-Vuelo--> ComprobacionOtrosVuelosHandler")
#         if not request.error:
#             o_vuelo = request.env['leulit.vuelo']
#             vuelo = o_vuelo.browse(request.vuelo_id)
#             vuelo_prevuelo = o_vuelo.search([('estado', '=', 'prevuelo'),('helicoptero_id', '=', vuelo.helicoptero_id.id),('fechasalida', '<=', vuelo.fechasalida),('codigo', '!=', vuelo.codigo)], order='fechasalida', limit=1)
#             if vuelo_prevuelo:
#                 raise UserError ('Este vuelo no puede pasar a cerrado. EL HELICÓPTERO ESTÁ EN EL VUELO %s Y ESTE ES ANTERIOR Y NO ESTÁ CERRADO' % vuelo_prevuelo.codigo)
#             vuelo_postvuelo = o_vuelo.search([('estado','=','postvuelo'),('helicoptero_id', '=', vuelo.helicoptero_id.id)], order='fechasalida', limit=1):
#             if vuelo_postvuelo:
#                 raise UserError ('Este vuelo no puede pasar a cerrado. EL HELICÓPTERO ESTÁ EN EL VUELO %s Y ESTE ESTÁ EN POST-VUELO' % vuelo_postvuelo.codigo)
#             vuelo_cerrado = o_vuelo.search([('estado', '=', 'cerrado'),('helicoptero_id', '=', vuelo.helicoptero_id.id),('fechasalida', '>=', vuelo.fechasalida)], order='fechasalida', limit=1)
#             if vuelo_cerrado:
#                 raise UserError ('Este vuelo no puede pasar a cerrado. EL HELICÓPTERO ESTÁ EN EL VUELO %s Y ESTE ES POSTERIOR Y ESTA CERRADO' % vuelo_cerrado.codigo)
#         return super().handle(request)


class ComprobacionUsuarioPilotoHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionUsuarioPilotoHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            if not ((vuelo.piloto_id and vuelo.piloto_id.partner_id.user_ids and vuelo.piloto_id.partner_id.user_ids.id == request.uid) or (vuelo.piloto_supervisor_id and vuelo.piloto_supervisor_id.partner_id.user_ids and vuelo.piloto_supervisor_id.partner_id.user_ids.id == request.uid)):
                raise UserError ('Solo el piloto o el piloto supervisor pueden cambiar el estado del vuelo a postvuelo')
        return super().handle(request)


class ComprobacionDescansoHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionDescansoHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)

            sw = False
            swPrimerVuelo = True
            hPrimerVuelo = 0.0
            totalTiempoVuelo = round(vuelo.tiemposervicio, 2)
            hSalida = vuelo.horasalida
            vuelos_obj = o_vuelo.search([('id','!=',vuelo.id),('estado','=','cerrado'),('fechavuelo','=',vuelo.fechavuelo),('piloto_id','=',vuelo.piloto_id.id),('horasalida','<',hSalida)], order="horasalida desc")
            for obj_vuelo in vuelos_obj:
                if (round(obj_vuelo.horallegada + 0.05, 2) >= round(hSalida, 2)) and swPrimerVuelo == True:
                    hSalida = obj_vuelo.horasalida
                    totalTiempoVuelo = totalTiempoVuelo + obj_vuelo.tiemposervicio
                    sw = True
                else:
                    if sw == True:
                        if totalTiempoVuelo > 3:
                            raise UserError (f'Se debe respetar el descanso de los Pilotos. Total tiempo de vuelo: {totalTiempoVuelo}')
                    else:
                        if (round(obj_vuelo.horallegada + 0.05, 2) >= round(hSalida, 2)):
                            hSalida = obj_vuelo.horasalida
                            totalTiempoVuelo = totalTiempoVuelo + obj_vuelo.tiemposervicio
                        else:
                            if swPrimerVuelo == True:
                                hSalida = obj_vuelo.horasalida
                                totalTiempoVuelo = obj_vuelo.tiemposervicio
                                swPrimerVuelo = False
                                hPrimerVuelo = round(obj_vuelo.horallegada, 2)
                            else:
                                descanso = round(totalTiempoVuelo * 20 / 60, 2)
                                if ((round(hPrimerVuelo + descanso, 2)) > round(vuelo.horasalida, 2)):
                                    #raise UserError ('Se debe respetar el descanso de los Pilotos')
                                    raise UserError(f'Se debe respetar el descanso de los Pilotos. Hora llega vuelo anterior: {hPrimerVuelo}, Descanso requerido: {descanso}, Hora siguiente vuelo: {vuelo.horasalida}')
        return super().handle(request)


class ComprobacionHelicopteroHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionHelicopteroHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            if vuelo.helicoptero_id.statemachine == 'En taller':
                raise UserError ('Este helicoptero está en Taller')
            if vuelo.isHelicopterBlocked(vuelo.helicoptero_id.id, vuelo.fechavuelo):
                raise UserError ('Este helicoptero tiene una anomalía/discrepancia sin firmar y no puede ser utilizado')
        return super().handle(request)


class ComprobacionOverlapPartesEscuelaVueloHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionOverlapPartesEscuelaVueloHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            o_parteescuela = request.env['leulit.parte_escuela']
            vuelo = o_vuelo.browse(request.vuelo_id)

            #verificar que no exista un vuelo para ese helicoptero posterior en estado diferente de cancelado o prevuelo
            vuelos_ids = o_vuelo.search([('id','!=',vuelo.id),('helicoptero_id','=',vuelo.helicoptero_id.id),('fechasalida', '>=', vuelo.fechasalida),('estado','!=','cancelado'),('estado','!=','prevuelo')])
            if vuelos_ids.ids and len(vuelos_ids.ids) > 0:
                raise UserError ('Existe un parte de vuelo con el mismo helicóptero, posterior a la fecha indicada, en estado Post-Vuelo. Parte de vuelo: %s' % (vuelos_ids[0].codigo))

            #verificar que no exista un vuelo para ese helicoptero anterior en estado prevuelo
            vuelos_ids = o_vuelo.search([('id','!=',vuelo.id),('helicoptero_id','=',vuelo.helicoptero_id.id),('fechasalida', '<=', vuelo.fechasalida),('estado','=','prevuelo')])
            if vuelos_ids.ids and len(vuelos_ids.ids) > 0:
                raise UserError ('Existe un parte de vuelo con el mismo helicóptero, anterior a la fecha indicada, en estado Prevuelo. Parte de vuelo: %s' % (vuelos_ids[0].codigo))

            #verificar que no exista un vuelo para ese piloto anterior en estado prevuelo
            vuelos_ids = o_vuelo.search([('id','!=',vuelo.id),('piloto_id','=',vuelo.piloto_id.id),('fechasalida', '<=', vuelo.fechasalida),('estado','=','prevuelo')])
            if vuelos_ids.ids and len(vuelos_ids.ids) > 0:
                raise UserError ('Existe un parte de vuelo con el mismo piloto, anterior a la fecha indicada, en estado Prevuelo. Parte de vuelo: %s' % (vuelos_ids[0].codigo))

            # Se comprueba que la tripulación del vuelo no esté en otro parte de vuelo en estado postvuelo o cerrado
            for parte_vuelo in o_vuelo.search([('estado','in',['postvuelo','cerrado']),('fechavuelo','=',vuelo.fechavuelo)]):
                if parte_vuelo.tiemposervicio > 0:
                    horallegada = parte_vuelo.horallegada
                else:
                    horallegada = parte_vuelo.horallegadaprevista
                # Verifica si dos vuelos se solapan en el tiempo.
                # True si los vuelos se solapan, False en caso contrario.
                if not (vuelo.horallegada <= parte_vuelo.horasalida or vuelo.horasalida >= horallegada):
                    tripulacion = ['piloto_id', 'operador', 'verificado', 'alumno']
                    for tripulante in tripulacion:
                        if getattr(vuelo, tripulante):
                            if getattr(parte_vuelo.piloto_id, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId() or getattr(parte_vuelo.operador, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId() or getattr(parte_vuelo.verificado, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId() or getattr(parte_vuelo.alumno, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId():
                                if tripulante == 'piloto_id':
                                    raise UserError ('Este vuelo no puede pasar a postvuelo. EL PILOTO ESTÁ EN UN VUELO EN ESTADO POST-VUELO O CERRADO (SOLAPAMIENTO)')
                                raise UserError (f'Este vuelo no puede pasar a postvuelo. EL {tripulante.upper()} ESTÁ EN UN VUELO EN ESTADO POST-VUELO O CERRADO (SOLAPAMIENTO)')

            # cojer el responsable del vuelo en caso de que fuera un vuelo de escuela.
            if vuelo.piloto_supervisor_id:
                objpiloto = vuelo.piloto_supervisor_id
            else:
                objpiloto = vuelo.piloto_id

            #  Verificar que no exista un parte de escuela donde se solape el profesor.
            if objpiloto.profesor:
                partes_ids = o_parteescuela.search([('profesor','=',objpiloto.profesor.id),('fecha','=',vuelo.fechavuelo),('hora_end','>=',vuelo.horasalida),('hora_start','<=',vuelo.horallegadaprevista),('estado','=','cerrado')])
                if partes_ids.ids and len(partes_ids.ids) > 0:
                    raise UserError ('El piloto o el piloto supervisor esta de profesor en un parte de escuela para la fecha y hora indicada. Parte de escuela: %s' % (partes_ids[0].id))

        return super().handle(request)



class ComprobacionParteEscuelaHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        parteescuela = False
        _logger.error("-Vuelo--> ComprobacionParteEscuelaHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            if not vuelo.parte_escuela_id:
                if (vuelo.alumno or vuelo.verificado) and not vuelo.silabus_ids :
                    raise UserError ('No se han introducido la información del Silabus')
                if vuelo.silabus_ids and (not vuelo.comentario_escuela or not vuelo.valoracion_escuela):
                    raise UserError ('Se tiene que rellenar el comentario y la valoración en el parte de vuelo')
                if vuelo.silabus_ids:
                    profesor_id = 0
                    if vuelo.piloto_supervisor_id:
                        profesor_id = vuelo.piloto_supervisor_id.partner_id.getProfesor()
                    else:
                        profesor_id = vuelo.piloto_id.partner_id.getProfesor()
                    parte_vals = {
                        'name'              : vuelo.codigo,
                        'comentario'        : vuelo.comentario_escuela,
                        'vuelo_id'          : vuelo.id,
                        'profesor'          : profesor_id,
                        'fecha'             : vuelo.fechavuelo,
                        'hora_start'        : vuelo.horasalida,
                        'hora_end'          : vuelo.horallegada,
                        'tiempo'            : vuelo.tiemposervicio,
                        'valoracion'        : vuelo.valoracion_escuela,
                        'estado'            : 'pendiente',
                    }
                    parteescuela = request.env['leulit.parte_escuela'].create(parte_vals)
                    for item in vuelo.silabus_ids:
                        item.rel_parte_escuela = parteescuela.id
                        if item.sil_test == True:
                            if not item.rel_docs:
                                raise UserError('Este Parte contiene un Silabus TEST que debe contener archivos adjuntos obligatorios.')
                            if item.nota == -1:
                                raise UserError('Este Parte contiene un Silabus TEST que debe contener nota obligatoria.')
                        if item.sil_valoracion == True:
                            if not item.valoracion:
                                raise UserError('Este Parte contiene una valoración en el Silabus que debe tener un valor obligatorio.')
                    vuelo.parte_escuela_id = parteescuela.id
            else:
                parteescuela = vuelo.parte_escuela_id
        request.env.cr.commit()
        if parteescuela:
            parteescuela.updateTiempos()
            _logger.error('Parte de escuela creado -> %r', parteescuela)
        request.env.cr.commit()

        return super().handle(request)



class ComprobacionDatosGeneralesHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionDatosGeneralesHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)

            if vuelo.airtime < 0 :
                raise UserError('Valor Air Time no válido')
            if vuelo.airtime > vuelo.tiemposervicio:
                raise UserError ('Valor Air Time no puede ser mayor o igual que el tiempo de servicio')
            if vuelo.tiemposervicio > 3.0:
                raise UserError('El valor del tiempo previsto de vuelo no puede ser superior a 3 horas')
            if vuelo.uso_gancho > vuelo.tiemposervicio:
                raise UserError ('El tiempo de uso del gancho no puede ser superior al tiempo del servicio realizado.')
            if request.tipo_helicoptero != "EC120B":
                if vuelo.tacomllegada <= 0:
                    raise UserError('Valor tacómetro de llegada no válido')
                if vuelo.tacomllegada <= vuelo.tacomsalida:
                    raise UserError('Valor tacómetro de llegada debe ser superior al de salida')
            else:
                if vuelo.ngvuelo <= 0:
                    raise UserError('Valor NG no válido')
                if vuelo.nfvuelo <= 0:
                    raise UserError('Valor NF no válido')
            if not vuelo.helicoptero_id.horas_remanente > vuelo.airtime:
                raise UserError('El tiempo de vuelo previsto (%s) excede el número de horas disponibles (%s) para esta máquina' % (utilitylib.leulit_float_time_to_str(vuelo.airtime),utilitylib.leulit_float_time_to_str(vuelo.helicoptero_id.horas_remanente)))

        return super().handle(request)


class ComprobacionDatosCombustibleHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionDatosCombustibleHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)

            if vuelo.consumomedio_vuelo == 0:
                raise UserError("El valor del consumo medio esta a 0, revisa el parte de vuelo.")
            if vuelo.fuelllegada <= 0:
                raise UserError ('Cantidad combustible llegada no válida')
            if vuelo.fuelsalida  <= vuelo.fuelllegada:
                raise UserError('Cantidad combustible salida es inferior al combustible mínimo')

        return super().handle(request)


class UpdateProximoVueloHandler(vuelo.AbstractHandler):
    
    def handle(self, request:Any) -> Any:
        _logger.error("-Vuelo--> UpdateProximoVueloHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)

            vuelos_obj = o_vuelo.search([('helicoptero_id', "=", vuelo.helicoptero_id.id),('estado','=','prevuelo'),('fechasalida', '>', vuelo.fechasalida)], order='fechasalida', limit=1)
            for obj_vuelo in vuelos_obj:
                obj_vuelo.write({'tacomsalida': vuelo.tacomllegada, 'editfuelrem': vuelo.fuelllegada})
        request.env.cr.commit()
        return super().handle(request)