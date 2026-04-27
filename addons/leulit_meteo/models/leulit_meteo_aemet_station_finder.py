# -*- coding: utf-8 -*-
"""Buscador interactivo del inventario de estaciones AEMET.

Cuando ``resolve_idema`` no consigue mapear un OACI a un indicativo AEMET
(p.ej. aeródromos pequeños como LELL Sabadell), este wizard permite al
usuario buscar manualmente la estación por nombre/provincia/indicativo y
aplicar el código resultante al registro ``leulit.meteo.metar`` que ha
originado el lookup.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .leulit_meteo_aemet_service import AemetOpenDataService

_logger = logging.getLogger(__name__)


class LeulitMeteoAemetStationFinder(models.TransientModel):
    _name = 'leulit.meteo.aemet.station.finder'
    _description = 'Buscador de estaciones AEMET'

    metar_id = fields.Many2one(
        'leulit.meteo.metar',
        string='Reporte METAR',
        default=lambda self: self.env.context.get('default_metar_id'))
    search_term = fields.Char(
        string='Texto de búsqueda',
        help='Se busca (sin distinción de mayúsculas) en el nombre, '
             'provincia o indicativo de la estación.')
    result_ids = fields.One2many(
        'leulit.meteo.aemet.station.finder.line',
        'finder_id',
        string='Resultados')

    def _get_api_key(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'leulit_meteo.aemet_api_key', '').strip()

    def action_buscar(self):
        self.ensure_one()
        api_key = self._get_api_key()
        if not api_key:
            raise UserError(_(
                'No hay API key de AEMET configurada. Configúrela en '
                'Ajustes (parámetro leulit_meteo.aemet_api_key).'))

        inventario = AemetOpenDataService.get_inventario_estaciones(api_key)
        if not inventario:
            raise UserError(_(
                'No se ha podido descargar el inventario de estaciones '
                'AEMET. Compruebe la API key y la conexión.'))

        term = (self.search_term or '').strip().upper()
        if term:
            def match(e):
                campos = (
                    (e.get('nombre') or ''),
                    (e.get('provincia') or ''),
                    (e.get('indicativo') or ''),
                )
                return any(term in c.upper() for c in campos)
            matches = [e for e in inventario if match(e)]
        else:
            matches = list(inventario)

        matches = matches[:50]

        # Limpiar y recrear las líneas
        self.result_ids.unlink()
        Line = self.env['leulit.meteo.aemet.station.finder.line']
        for e in matches:
            Line.create({
                'finder_id': self.id,
                'indicativo': e.get('indicativo') or '',
                'nombre': e.get('nombre') or '',
                'provincia': e.get('provincia') or '',
                'altitud': str(e.get('altitud') or ''),
                'latitud': str(e.get('latitud') or ''),
                'longitud': str(e.get('longitud') or ''),
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


class LeulitMeteoAemetStationFinderLine(models.TransientModel):
    _name = 'leulit.meteo.aemet.station.finder.line'
    _description = 'Línea de resultados del buscador AEMET'
    _order = 'nombre'

    finder_id = fields.Many2one(
        'leulit.meteo.aemet.station.finder',
        required=True, ondelete='cascade')
    indicativo = fields.Char(string='Indicativo')
    nombre = fields.Char(string='Nombre')
    provincia = fields.Char(string='Provincia')
    altitud = fields.Char(string='Altitud (m)')
    latitud = fields.Char(string='Latitud')
    longitud = fields.Char(string='Longitud')

    def action_aplicar(self):
        """Escribe la estación seleccionada en el ``leulit.meteo.metar``
        que originó el wizard, y cierra la ventana modal."""
        self.ensure_one()
        finder = self.finder_id
        metar = finder.metar_id
        if not metar:
            raise UserError(_(
                'No se ha encontrado el reporte METAR de origen. '
                'Cierre el buscador y vuelva a abrirlo desde la ficha.'))

        metar.write({
            'station_code': self.indicativo or False,
            'station_name': self.nombre or False,
        })
        return {'type': 'ir.actions.act_window_close'}
