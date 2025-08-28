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


class VueloChainToPostvueloRequest():
    _name = "VueloChainToPostvueloRequest"
    
    error = None
    errorCode = "000"
    errormsg = ""
    

    env = None
    vuelo_id = 0
    uid = 0
    tipo_helicoptero = ''


class ComprobacionTripulacionEnVuelosPostvueloHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionTripulacionEnVuelosPostvueloHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            for parte_vuelo in o_vuelo.search([('estado','=','postvuelo')]):
                # Se comprueba que la tripulación del vuelo no esté en otro parte de vuelo en estado postvuelo
                tripulacion = ['piloto_id', 'operador', 'verificado', 'alumno']
                for tripulante in tripulacion:
                    if getattr(vuelo, tripulante):
                        if getattr(parte_vuelo.piloto_id, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId() or getattr(parte_vuelo.operador, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId() or getattr(parte_vuelo.verificado, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId() or getattr(parte_vuelo.alumno, 'getPartnerId')() == getattr(vuelo, tripulante).getPartnerId():
                            if tripulante == 'piloto_id':
                                raise UserError ('Este vuelo no puede pasar a postvuelo. EL PILOTO ESTÁ EN UN VUELO EN ESTADO POST-VUELO')
                            raise UserError (f'Este vuelo no puede pasar a postvuelo. EL {tripulante.upper()} ESTÁ EN UN VUELO EN ESTADO POST-VUELO')

            request.env.cr.commit()
        return super().handle(request)


class ComprobacionChecksHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionChecksHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            if not vuelo.checklist_realizado:
                raise UserError ('Este vuelo no puede pasar a postvuelo. NO HA MARCADO LA INSPECCIÓN PREVUELO CÓMO REALIZADA')
            vuelo.check_first_flight()
            if not vuelo.briefing_realizado:
                raise UserError ('Este vuelo no puede pasar a postvuelo. NO HA MARCADO EL BRIEFING AERODROMO SALIDA, LLEGADA Y ALTERNATIVOS CÓMO REALIZADO')

            request.env.cr.commit()
        return super().handle(request)


class ComprobacionTripulantesTipoActividadHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionChecksHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            if vuelo.numpax > 0:
                if vuelo.tipo_actividad not in ['AOC', 'NCO']:
                    raise UserError("Los unicos tipos de vuelo que pueden tener pasajeros son AOC y NCO.")
            if vuelo.numpae > 0:
                if vuelo.tipo_actividad in ['AOC', 'NCO']:
                    raise UserError("Los tipos de vuelo AOC y NCO no pueden tener tripulantes con funciones en el vuelo.")
            request.env.cr.commit()
        return super().handle(request)


class ComprobacionUsuarioPilotoHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionUsuarioPilotoHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            if not ((vuelo.piloto_id and vuelo.piloto_id.partner_id.user_ids and vuelo.piloto_id.partner_id.user_ids.id == request.uid) or (vuelo.piloto_supervisor_id and vuelo.piloto_supervisor_id.partner_id.user_ids and vuelo.piloto_supervisor_id.partner_id.user_ids.id == request.uid)):
                raise UserError ('Solo el piloto o el piloto supervisor pueden cambiar el estado del vuelo a postvuelo')
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
                if not (vuelo.horallegadaprevista <= parte_vuelo.horasalida or vuelo.horasalida >= horallegada):
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
        _logger.error("-Vuelo--> ComprobacionParteEscuelaHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)
            vts = False
            spic = False
            doblemando = False
            for sil in vuelo.silabus_ids:
                if vts and not sil.rel_silabus.vts:
                    raise UserError ('VUELO VTS: Todos los silabus deben ser VTS o VBS o NBS.\nVUELO SPIC: Todos los silabus deben ser TV o VBDS.\nVUELO DOBLE MANDO: Todos los silabus deben ser VBD o VTD o IBD o NBD.')
                if spic and not sil.rel_silabus.spic:
                    raise UserError ('VUELO VTS: Todos los silabus deben ser VTS o VBS o NBS.\nVUELO SPIC: Todos los silabus deben ser TV o VBDS.\nVUELO DOBLE MANDO: Todos los silabus deben ser VBD o VTD o IBD o NBD.')
                if doblemando and not sil.rel_silabus.doblemando:
                    raise UserError ('VUELO VTS: Todos los silabus deben ser VTS o VBS o NBS.\nVUELO SPIC: Todos los silabus deben ser TV o VBDS.\nVUELO DOBLE MANDO: Todos los silabus deben ser VBD o VTD o IBD o NBD.')
                if sil.rel_silabus.vts:
                    vts = True
                    if vuelo.piloto_id.id != vuelo.alumno.piloto_id.id:
                        raise UserError ('VUELO VTS: El piloto y el alumno deben ser el mismo.')
                    elif not vuelo.piloto_supervisor_id:
                        raise UserError ('VUELO VTS: Debe tener un profesor supervisor.')
                if sil.rel_silabus.spic:
                    spic = True
                    if not vuelo.piloto_id or not vuelo.verificado or vuelo.operador or vuelo.piloto_supervisor_id or vuelo.alumno:
                        raise UserError ('VUELO SPIC: En el parte de vuelo debe tener un piloto(Instructor) y un verificado(Alumno).')
                    if vuelo.piloto_id.id == vuelo.verificado.id:
                        raise UserError ('VUELO SPIC: El piloto y el verificado deben ser diferentes.')
                if sil.rel_silabus.doblemando:
                    doblemando = True
                    if not vuelo.piloto_id or not vuelo.alumno or vuelo.operador or not vuelo.piloto_supervisor_id or vuelo.verificado:
                        raise UserError ('VUELO DOBLE MANDO: En el parte de vuelo debe tener un piloto(Alumno), un Alumno(Alumno) y un piloto supervisor(Instructor).')
                    if vuelo.piloto_id.id != vuelo.alumno.piloto_id.id:
                        raise UserError ('VUELO DOBLE MANDO: El piloto y el alumno deben ser el mismo.')

        return super().handle(request)


class ComprobacionDatosGeneralesHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionDatosGeneralesHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)

            if vuelo.distanciatotalprevista == 0:
                raise UserError('Distancia total prevista no válida ')
            if vuelo.numtripulacion == 0:
                raise UserError('Número de personas tripulación no válido ')
            if vuelo.tiempoprevisto > 3.0:
                raise UserError('El valor del tiempo previsto de vuelo no puede ser superior a 3 horas')
            if not vuelo.notam_revisado:
                raise UserError ('Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM')
            if (vuelo.meteo is False):
                raise UserError('Es necesario especificar la información meteorológica')
            if (vuelo.horasalida <= 0):
                raise UserError('Hora de salida no válida')
            if (vuelo.tacomsalida <= 0) and (request.tipo_helicoptero != "EC120B"):
                raise UserError('Valor tacómetro de salida no válido')
            if vuelo.oilqty < 0:
                raise UserError('Es obligatorio indicar la cantidad de aceite añadida. 0 es un valor válido.')
            if not vuelo.helicoptero_id.horas_remanente > vuelo.tiempoprevisto:
                raise UserError('El tiempo de vuelo previsto (%s) excede el número de horas disponibles (%s) para esta máquina' % (utilitylib.leulit_float_time_to_str(vuelo.tiempoprevisto),utilitylib.leulit_float_time_to_str(vuelo.helicoptero_id.horas_remanente)))
            if (not vuelo.valid_takeoff_longcg or not vuelo.valid_takeoff_latcg or not vuelo.valid_landing_longcg or not vuelo.valid_landing_latcg):
                raise UserError('El peso y centrado no es correcto.')
            if not vuelo.performance:
                raise UserError('No hay Performance.')
            if vuelo.pasajeros_wb != sum([vuelo.numtripulacion,vuelo.numpax,vuelo.numpae]):
                raise UserError('La suma de tripulantes, (pax /AESA) y (AL/PA/PE/PAE/PO) no es igual al numero de pesos introducidos en la Carga y Centrado.')
            if vuelo.ruta_id.water_zone:
                if not vuelo.flotadores:
                    raise UserError("La ruta establecida tiene areas autorotativas sobre el agua, marca el check de Flotadores.")
            if not vuelo.vuelo_tipo_line:
                raise UserError('No hay comentario logbook')

        return super().handle(request)


class ComprobacionDatosCombustibleHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionDatosCombustibleHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            vuelo = o_vuelo.browse(request.vuelo_id)

            if vuelo.consumomedio_vuelo == 0:
                raise UserError("El valor del consumo medio esta a 0, revisa el parte de vuelo.")
            if vuelo.combustiblelanding <= 0:
                raise UserError ('Combustible previsto aterrizaje no válido')
            if vuelo.fuelsalida < vuelo.combustibleminimo:
                raise UserError('Cantidad combustible salida es inferior al combustible mínimo')
            if vuelo.fuelsalida > 170 and request.tipo_helicoptero == "CABRI G2":
                raise UserError('Valor combustible al despegue excede el límite máximo')
            if vuelo.fuelsalida > 110 and request.tipo_helicoptero == "R22":
                raise UserError('Valor combustible al despegue excede el límite máximo')
            if vuelo.fuelsalida > 180 and request.tipo_helicoptero == "R44":
                raise UserError('Valor combustible al despegue excede el límite máximo')
            if vuelo.fuelsalida > 410 and request.tipo_helicoptero == "EC120B":
                raise UserError('Valor combustible al despegue excede el límite máximo')

        return super().handle(request)


class ComprobacionPerfilesFormacionHandler(vuelo.AbstractHandler):

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> ComprobacionPerfilesFormacionHandler")
        if not request.error:
            o_vuelo = request.env['leulit.vuelo']
            o_pf = request.env['leulit.perfil_formacion']
            o_alumno = request.env['leulit.alumno']
            vuelo = o_vuelo.browse(request.vuelo_id)
            exists_pf = False
            if vuelo.piloto_supervisor_id:
                tripulante_alumno = o_alumno.search([('partner_id','=',vuelo.piloto_supervisor_id.getPartnerId())])
            else:
                tripulante_alumno = o_alumno.search([('partner_id','=',vuelo.piloto_id.getPartnerId())])

            tipo_formacion = request.env['leulit.vuelostipo'].search([('name','=','Formación interna')])
            if any(tipo_formacion.id == tipo.id for tipo in vuelo.vuelo_tipo_line.vuelo_tipo_id):
                domain = [('alumno','=',tripulante_alumno.id),('inactivo','=',False)]
            else:
                domain = [('alumno','=',tripulante_alumno.id),('inactivo','=',False),('tipo_helicoptero','=',request.tipo_helicoptero)]
                
            if tripulante_alumno:
                for pf in o_pf.search(domain):
                    if any(pf.vuelo_tipo_id.id == tipo.id for tipo in vuelo.vuelo_tipo_line.vuelo_tipo_id):
                        exists_pf = True
                        for curso in pf.cursos:
                            if curso.semaforo_dy == 'red':
                                raise UserError ('%s tiene el curso "%s" del perfil de formación "%s" con el semáforo en rojo desde el %s' % (tripulante_alumno.name,curso.descripcion,pf.name,curso.next_done_date))
                        for accion in pf.acciones_new:
                            if accion.semaforo_dy == 'red':
                                raise UserError ('%s tiene la acción "%s" del perfil de formación "%s" con el semáforo en rojo desde el %s' % (tripulante_alumno.name,accion.accion.name,pf.name,accion.next_done_date))

                if vuelo.ruta_id and vuelo.ruta_id.water_zone:
                    for pf in o_pf.search([('alumno','=',tripulante_alumno.id),('inactivo','=',False),('water_zone','=',True)]):
                        for curso in pf.cursos:
                            if curso.semaforo_dy == 'red':
                                raise UserError ('%s tiene el curso "%s" del perfil de formación "%s" con el semáforo en rojo desde el %s' % (tripulante_alumno.name,curso.descripcion,pf.name,curso.next_done_date))
                        for accion in pf.acciones_new:
                            if accion.semaforo_dy == 'red':
                                raise UserError ('%s tiene la acción "%s" del perfil de formación "%s" con el semáforo en rojo desde el %s' % (tripulante_alumno.name,accion.accion.name,pf.name,accion.next_done_date))

                if not exists_pf:
                    raise UserError ('%s no tiene el perfil de formación para la operación y el tipo de aeronave del parte de vuelo' % (tripulante_alumno.name))

            if vuelo.operador:
                tripulante_alumno_op = o_alumno.search([('partner_id','=',vuelo.operador.getPartnerId())])
                exists_pf_op = False
                if tripulante_alumno_op:
                    for pf in o_pf.search([('alumno','=',tripulante_alumno_op.id),('inactivo','=',False),('operador','=',True)]):
                        if any(pf.vuelo_tipo_id.id == tipo.id for tipo in vuelo.vuelo_tipo_line.vuelo_tipo_id):
                            exists_pf_op = True
                            for curso in pf.cursos:
                                if curso.semaforo_dy == 'red':
                                    raise UserError ('%s tiene el curso "%s" del perfil de formación "%s" con el semáforo en rojo desde el %s' % (tripulante_alumno_op.name,curso.descripcion,pf.name,curso.next_done_date))
                            for accion in pf.acciones_new:
                                if accion.semaforo_dy == 'red':
                                    raise UserError ('%s tiene la acción "%s" del perfil de formación "%s" con el semáforo en rojo desde el %s' % (tripulante_alumno_op.name,accion.accion.name,pf.name,accion.next_done_date))

                    if not exists_pf:
                        raise UserError ('%s no tiene el perfil de formación para la operación y el tipo de aeronave del parte de vuelo' % (tripulante_alumno_op.name))

        return super().handle(request)