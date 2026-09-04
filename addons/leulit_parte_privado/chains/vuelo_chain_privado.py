# -*- encoding: utf-8 -*-
"""Cadenas paralelas del parte privado: mismos eslabones que el flujo normal, importados,
menos los que no aplican a un vuelo NCO transcrito (meteo, W&B, performance, escuela, perfiles)."""
from typing import Any
from odoo.exceptions import UserError
from odoo.addons.leulit import utilitylib
from odoo.addons.leulit_operaciones import vuelo, vuelo_chain_postvuelo as post, vuelo_chain_cerrado as cerr

import logging
_logger = logging.getLogger(__name__)


class DatosGeneralesPrivadoHandler(vuelo.AbstractHandler):
    """ComprobacionDatosGeneralesHandler de vuelo_chain_postvuelo sin meteo, C.G., performance ni pasajeros_wb."""

    def handle(self, request: Any) -> Any:
        _logger.error("-Vuelo--> DatosGeneralesPrivadoHandler")
        if not request.error:
            v = request.env['leulit.vuelo'].browse(request.vuelo_id)
            if v.distanciatotalprevista == 0:
                raise UserError('Distancia total prevista no válida ')
            if v.numtripulacion == 0:
                raise UserError('Número de personas tripulación no válido ')
            if v.tiempoprevisto > 3.0:
                raise UserError('El valor del tiempo previsto de vuelo no puede ser superior a 3 horas')
            if not v.notam_revisado:
                raise UserError('Este vuelo no puede pasar a postvuelo. NO HA REVISADO NOTAM')
            if v.horasalida <= 0:
                raise UserError('Hora de salida no válida')
            if v.tacomsalida <= 0 and request.tipo_helicoptero != "EC120B":
                raise UserError('Valor tacómetro de salida no válido')
            if v.oilqty < 0:
                raise UserError('Es obligatorio indicar la cantidad de aceite añadida. 0 es un valor válido.')
            if not v.helicoptero_id.horas_remanente > v.tiempoprevisto:
                raise UserError('El tiempo de vuelo previsto (%s) excede el número de horas disponibles (%s) para esta máquina' % (utilitylib.leulit_float_time_to_str(v.tiempoprevisto), utilitylib.leulit_float_time_to_str(v.helicoptero_id.horas_remanente)))
            if v.ruta_id.water_zone and not v.flotadores:
                raise UserError("La ruta establecida tiene areas autorotativas sobre el agua, marca el check de Flotadores.")
            if not v.vuelo_tipo_line:
                raise UserError('No hay comentario logbook')
        return super().handle(request)


def _enlazar(handlers):
    for a, b in zip(handlers, handlers[1:]):
        a.set_next(b)
    return handlers[0]


def chain_to_postvuelo():
    return _enlazar([
        post.ComprobacionTripulacionEnVuelosPostvueloHandler(),
        post.ComprobacionChecksHandler(),
        post.ComprobacionTripulantesTipoActividadHandler(),
        post.ComprobacionUsuarioPilotoHandler(),
        post.ComprobacionHelicopteroHandler(),
        post.ComprobacionOverlapPartesEscuelaVueloHandler(),
        DatosGeneralesPrivadoHandler(),
        post.ComprobacionDatosCombustibleHandler(),
        # omitidos: ComprobacionParteEscuelaHandler, ComprobacionPerfilesFormacionHandler (spec §3)
    ])


def chain_to_cerrado():
    # Igual que initChainToCerrado pero con ComprobacionDatosCombustibleHandler realmente enlazado
    # (el original lo pisa al asignar chain7 dos veces) y sin ComprobacionParteEscuelaHandler.
    return _enlazar([
        cerr.ComprobacionPresupuestoHandler(),
        cerr.ComprobacionChecksHandler(),
        cerr.ComprobacionUsuarioPilotoHandler(),
        cerr.ComprobacionDescansoHandler(),
        cerr.ComprobacionHelicopteroHandler(),
        # ponytail: initChainToCerrado tampoco lo lleva; aquí además auto-solaparía
        # (el vuelo ya está en postvuelo cuando corre esta cadena y la búsqueda de
        # vuelo_chain_cerrado.py no excluye el propio id). El solape ya se comprobó
        # en chain_to_postvuelo. Omitido: ComprobacionOverlapPartesEscuelaVueloHandler.
        cerr.ComprobacionDatosGeneralesHandler(),
        cerr.ComprobacionDatosCombustibleHandler(),
        cerr.UpdateProximoVueloHandler(),
    ])
