# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_rel_planoperacional_aerovia(models.Model):
	_name 			= "leulit.rel_planoperacional_aerovia"
	_description	= "leulit_rel_planoperacional_aerovia"


	@api.depends('aerovia_id.start_point_id.latitud')
	def _get_lat_origen(self):
		for item in self:
			item.latorigen = item.aerovia_id.start_point_id.latitud


	@api.depends('aerovia_id.start_point_id.longitud')
	def _get_lng_origen(self):
		for item in self:
			item.lngorigen = item.aerovia_id.start_point_id.longitud
		

	@api.depends('tiempoprevisto')
	def _get_str_horas(self):
		for item in self:
			valor = 0
			if item.tiempoprevisto:
				valor = item.tiempoprevisto
			item.strtiempoprevisto = utilitylib.leulit_float_time_to_str( valor )


	ruta_id = fields.Many2one('leulit.ruta', 'Ruta', required=True)
	vuelo_id = fields.Many2one('leulit.vuelo', 'Vuelo')
	aerovia_id = fields.Many2one('leulit.ruta_aerovia', 'Aerovía')
	aerovia_ruta_id = fields.Many2one('leulit.rel_ruta_aerovia', 'Aerovía Ruta')
	distancia = fields.Float(related='aerovia_id.distancia',string='NM',store=True)
	rumbo = fields.Float(related='aerovia_id.rumbo',string='Rumbo (º)',store=True)
	altitudprevista = fields.Float(related='aerovia_ruta_id.altitudprevista',string='Altitud prevista (p)',store=False)
	altitudseguridad = fields.Float(related='aerovia_id.altitudseguridad',string='Altitud seguridad (p)',store=False)
	tiempoprevisto = fields.Float(string='Tiempo previsto',readonly=False)
	strtiempoprevisto = fields.Char(compute='_get_str_horas',string='Tiempo previsto (hh:mm)',store=True)
	latorigen = fields.Float(compute='_get_lat_origen',string='Lat. Origen')
	lngorigen = fields.Float(compute='_get_lng_origen',string='Lng. Origen')
