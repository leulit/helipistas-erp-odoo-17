# -*- coding: utf-8 -*-
"""Proveedor METAR basado en AEMET OpenData.

AEMET OpenData no expone METAR oficiales, así que esta implementación
construye un texto tipo METAR a partir de la observación horaria más
reciente de la estación AEMET correspondiente.
"""

import logging
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .leulit_meteo_metar_provider import MetarProvider, register_provider
from .leulit_meteo_aemet_service import AemetOpenDataService, ICAO_TO_IDEMA

_logger = logging.getLogger(__name__)


@register_provider
class AemetMetarProvider(MetarProvider):
    """AEMET OpenData (España)."""

    code = 'aemet'
    label = 'AEMET (España)'

    CONFIG_PARAM = 'leulit_meteo.aemet_api_key'

    # ---------- helpers ----------

    def _get_api_key(self, env, raise_if_missing=True):
        key = env['ir.config_parameter'].sudo().get_param(self.CONFIG_PARAM)
        if not key and raise_if_missing:
            raise UserError(_(
                'No se ha configurado la API Key de AEMET. '
                'Configúrela en Ajustes → Meteorología → AEMET API Key. '
                'Puede obtener una en https://opendata.aemet.es/'))
        return key

    # ---------- interfaz MetarProvider ----------

    def validate(self, env):
        key = self._get_api_key(env, raise_if_missing=False)
        return bool(key) and AemetOpenDataService.validate_api_key(key)

    def prefill_station_code(self, icao_code):
        if not icao_code:
            return None
        return ICAO_TO_IDEMA.get(icao_code.upper().strip())

    def coverage(self, icao_code):
        """AEMET solo cubre estaciones en territorio español."""
        if not icao_code:
            return True  # acepta consultas por station_code
        prefix = icao_code[:2].upper()
        return prefix in ('LE', 'GC', 'GE')

    def get_observation(self, env, icao_code=None, station_code=None):
        api_key = self._get_api_key(env)
        data = AemetOpenDataService.get_metar_like(
            api_key,
            icao_code=icao_code,
            idema_code=station_code,
        )
        if not data:
            return None
        return {
            'provider': self.code,
            'icao': data.get('icao') or (
                icao_code.upper().strip() if icao_code else None),
            'station_code': data.get('idema'),
            'station_name': data.get('station_name'),
            'observation_time': data.get('observation_time'),
            'temperatura': data.get('temperatura'),
            'dewpoint': data.get('dewpoint'),
            'humidity': data.get('humidity'),
            'wind_direction': data.get('wind_direction'),
            'wind_speed_kt': data.get('wind_speed_kt'),
            'wind_gust_kt': data.get('wind_gust_kt'),
            'visibility_m': data.get('visibility_m'),
            'qnh': data.get('qnh'),
            'pressure': data.get('pressure'),
            'precipitation': data.get('precipitation'),
            'latitude': data.get('latitude'),
            'longitude': data.get('longitude'),
            'elevation': data.get('elevation_m'),
            'raw_metar': data.get('raw_metar'),
        }
