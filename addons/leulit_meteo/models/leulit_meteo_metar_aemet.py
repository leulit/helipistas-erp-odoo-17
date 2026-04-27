# -*- coding: utf-8 -*-
"""Proveedor METAR/TAF/SIGMET basado en AEMET OpenData.

A diferencia de la versión anterior (que sintetizaba un METAR a partir
de la observación horaria), este proveedor descarga los **mensajes
oficiales** que AEMET expone en OpenData:

    * METAR  por OACI
    * TAF    por OACI
    * SIGMET por FIR (LECM/LECB/GCCC)

Se apoya en la tabla ``leulit.meteo.icao.reference`` para:
    * Saber la FIR del aeródromo (necesario para SIGMET).
    * Sustituir, si procede, un OACI sin METAR propio (helipuerto)
      por el aeródromo de referencia.
"""

import logging

from odoo.exceptions import UserError
from odoo.tools.translate import _

from .leulit_meteo_aemet_service import AemetOpenDataService
from .leulit_meteo_checkwx_service import CheckWXService
from .leulit_meteo_metar_parser import parse_metar
from .leulit_meteo_metar_provider import MetarProvider, register_provider

_logger = logging.getLogger(__name__)


@register_provider
class AemetMetarProvider(MetarProvider):
    """AEMET OpenData (España): METAR + TAF + SIGMET."""

    code = 'aemet'
    label = 'AEMET (España)'

    CONFIG_PARAM = 'leulit_meteo.aemet_api_key'

    # ---------- helpers ----------

    def _get_api_key(self, env, raise_if_missing=True):
        key = env['ir.config_parameter'].sudo().get_param(self.CONFIG_PARAM)
        if not key and raise_if_missing:
            raise UserError(_(
                'No se ha configurado la API Key de AEMET. '
                'Configúrela en Ajustes -> Meteorología -> AEMET API Key. '
                'Puede obtener una en https://opendata.aemet.es/'))
        return key

    # ---------- interfaz MetarProvider ----------

    def validate(self, env):
        key = self._get_api_key(env, raise_if_missing=False)
        return bool(key) and AemetOpenDataService.validate_api_key(key)

    def _get_checkwx_key(self, env):
        return env['ir.config_parameter'].sudo().get_param(
            'leulit_meteo.checkwx_api_key', '')

    def get_observation(self, env, icao_code=None, station_code=None):
        """Devuelve un dict normalizado con METAR + TAF + SIGMET RAW."""
        if not icao_code:
            return None
        api_key = self._get_api_key(env)
        icao_in = icao_code.upper().strip()
        _logger.info("AEMET.get_observation: inicio para icao_in=%s", icao_in)

        ref = env['leulit.meteo.icao.reference'].sudo().resolve(icao_in)
        if ref is None:
            _logger.warning(
                "AEMET provider: OACI %s no está en "
                "leulit.meteo.icao.reference; consultando directo y sin "
                "FIR (no se podrá traer SIGMET).", icao_in)
            ref = {
                'icao_consultar': icao_in,
                'fir': None,
                'usa_referencia': False,
                'nombre': icao_in,
                'ref_nombre': None,
                'proveedor_oficial': 'aemet',
                'station_code': None,
                'station_nombre': None,
                'station_distancia_km': None,
                'ref_distancia_km': None,
            }

        icao_consultar = ref['icao_consultar']
        fir = ref['fir']
        usa_referencia = ref['usa_referencia']
        ref_nombre = ref['ref_nombre']
        station_name = ref.get('nombre') or icao_consultar
        proveedor_oficial = ref.get('proveedor_oficial', 'aemet')
        _logger.info(
            "AEMET.get_observation: resolve(%s) → icao_consultar=%s "
            "usa_referencia=%s fir=%s proveedor_oficial=%s station_code=%s",
            icao_in, icao_consultar, usa_referencia, fir,
            proveedor_oficial, ref.get('station_code'))

        # --- METAR/TAF/SIGMET oficiales ---
        raw_metar = AemetOpenDataService.get_message(
            'METAR', icao_consultar, api_key)
        raw_taf = AemetOpenDataService.get_message(
            'TAF', icao_consultar, api_key)
        raw_sigmet = (
            AemetOpenDataService.get_message('SIGMET', fir, api_key)
            if fir else None
        )
        _logger.info(
            "AEMET.get_observation: AEMET directo para %s → "
            "metar=%s taf=%s sigmet=%s",
            icao_consultar,
            bool(raw_metar), bool(raw_taf), bool(raw_sigmet))

        # AEMET sin datos → (1) CheckWX para el mismo ICAO; (2) aeródromo MET más próximo
        if not (raw_metar or raw_taf):
            _logger.info("AEMET.get_observation: %s sin datos en AEMET", icao_consultar)
            checkwx_key = self._get_checkwx_key(env)
            if checkwx_key:
                raw_metar = CheckWXService.get_metar(icao_consultar, checkwx_key)
                raw_taf = CheckWXService.get_taf(icao_consultar, checkwx_key)
                _logger.info(
                    "AEMET.get_observation: CheckWX directo %s → metar=%s taf=%s",
                    icao_consultar, bool(raw_metar), bool(raw_taf))

        # Si ni AEMET ni CheckWX tienen el ICAO → buscar aeródromo MET más próximo
        if not (raw_metar or raw_taf):
            _logger.info(
                "AEMET.get_observation: %s sin datos en ninguna fuente directa, "
                "buscando aeródromo MET próximo", icao_consultar)
            enrich = env['leulit.meteo.icao.reference'].sudo()._enrich_ref_icao(icao_consultar)
            _logger.info(
                "AEMET.get_observation: _enrich_ref_icao(%s) → %s",
                icao_consultar, enrich)
            if enrich and enrich.get('ref_icao'):
                new_icao = enrich['ref_icao']
                new_proveedor = enrich.get('proveedor_oficial', 'aemet')
                if new_proveedor != 'checkwx':
                    raw_metar = AemetOpenDataService.get_message('METAR', new_icao, api_key)
                    raw_taf = AemetOpenDataService.get_message('TAF', new_icao, api_key)
                if not (raw_metar or raw_taf):
                    checkwx_key = checkwx_key or self._get_checkwx_key(env)
                    if checkwx_key:
                        raw_metar = CheckWXService.get_metar(new_icao, checkwx_key)
                        raw_taf = CheckWXService.get_taf(new_icao, checkwx_key)
                if raw_metar or raw_taf:
                    icao_consultar = new_icao
                    usa_referencia = True
                    ref_nombre = enrich.get('ref_nombre') or new_icao
                    _logger.info(
                        "AEMET.get_observation: usando aeródromo próximo %s", new_icao)

        derived = parse_metar(raw_metar) if raw_metar else {}

        # --- METAR sintético de la estación AEMET más próxima ---
        raw_metar_est = None
        station_est_code = None
        station_est_nombre = None
        station_est_distancia_km = None

        station_code_ref = ref.get('station_code')
        station_nombre_ref = ref.get('station_nombre')
        station_dist_ref = ref.get('station_distancia_km')

        if station_code_ref and api_key:
            obs_list = AemetOpenDataService.get_observaciones_estacion(
                station_code_ref, api_key)
            last_obs = AemetOpenDataService.latest_observation(obs_list)
            if last_obs:
                parsed_obs = AemetOpenDataService.parse_observacion(last_obs)
                if parsed_obs:
                    raw_metar_est = AemetOpenDataService.build_metar_synthetic(
                        parsed_obs, icao_code=icao_in)
                    station_est_code = station_code_ref
                    station_est_nombre = station_nombre_ref or parsed_obs.get('station_name')
                    station_est_distancia_km = station_dist_ref

        # Sin ninguna fuente de datos disponible, devolver None
        if not (raw_metar or raw_taf or raw_sigmet or raw_metar_est):
            return None

        return {
            'provider': self.code,
            'icao': icao_in,
            'icao_consultar': icao_consultar,
            'usa_referencia': usa_referencia,
            'ref_icao': icao_consultar if usa_referencia else None,
            'ref_nombre': ref_nombre,
            'fir_code': fir,
            'station_code': station_code or None,
            'station_name': station_name,
            'raw_metar': raw_metar,
            'raw_taf': raw_taf,
            'raw_sigmet': raw_sigmet,
            'observation_time': derived.get('observation_time'),
            'temperatura': derived.get('temperatura'),
            'dewpoint': derived.get('dewpoint'),
            'wind_direction': derived.get('wind_direction'),
            'wind_speed_kt': derived.get('wind_speed_kt'),
            'wind_gust_kt': derived.get('wind_gust_kt'),
            'visibility_m': derived.get('visibility_m'),
            'qnh': derived.get('qnh'),
            'humidity': None,
            'pressure': None,
            'precipitation': None,
            'latitude': None,
            'longitude': None,
            'elevation': None,
            'raw_metar_est': raw_metar_est,
            'station_est_code': station_est_code,
            'station_est_nombre': station_est_nombre,
            'station_est_distancia_km': station_est_distancia_km,
            'ref_distancia_km': ref.get('ref_distancia_km'),
        }
