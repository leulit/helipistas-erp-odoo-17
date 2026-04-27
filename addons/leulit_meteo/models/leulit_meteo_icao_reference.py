# -*- coding: utf-8 -*-
import logging
import math

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Radio máximo en km para buscar aeródromo con METAR cerca de un OACI desconocido
_SEARCH_RADIUS_KM = 150


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fir_heuristic(lat, lon):
    """FIR por heurística de coordenadas cuando no hay registro en tabla."""
    if lat is not None and lat <= 30:
        return 'GCCC'
    if lat is not None and lon is not None and lon >= -1.5 and lat >= 40:
        return 'LECB'
    return 'LECM'


class LeulitMeteoIcaoReference(models.Model):
    _name = 'leulit.meteo.icao.reference'
    _description = 'Aeródromos de referencia OACI / FIR'
    _rec_name = 'icao'
    _order = 'icao'

    icao = fields.Char('OACI', size=4, required=True, index=True)
    nombre = fields.Char('Nombre del punto')
    fir = fields.Selection([
        ('LECM', 'LECM - Madrid'),
        ('LECB', 'LECB - Barcelona'),
        ('GCCC', 'GCCC - Canarias'),
    ], string='FIR', required=True)
    tiene_metar_propio = fields.Boolean(
        'Emite METAR propio', default=True,
        help='Si está desmarcado, usaremos el aeródromo de referencia '
             'para METAR/TAF.')
    ref_icao = fields.Char(
        'OACI de referencia', size=4,
        help='Aeródromo con METAR/TAF que usaremos cuando este punto no emita.')
    ref_nombre = fields.Char('Nombre del aeródromo de referencia')
    ref_distancia_km = fields.Float(
        'Distancia al aeródromo ref. (km)', digits=(6, 1))

    # Coordenadas del OACI (rellenas en auto-resolución)
    latitud = fields.Float('Latitud', digits=(10, 6))
    longitud = fields.Float('Longitud', digits=(10, 6))

    # Estación AEMET convencional más próxima
    station_code = fields.Char('Cód. Estación AEMET', size=10)
    station_nombre = fields.Char('Estación AEMET')
    station_distancia_km = fields.Float(
        'Distancia estación (km)', digits=(6, 1))

    # Proveedor del METAR oficial
    proveedor_oficial = fields.Selection([
        ('aemet', 'AEMET'),
        ('checkwx', 'CheckWX'),
        ('ninguno', 'Ninguno'),
    ], string='Proveedor METAR oficial', default='aemet')

    auto_resolved = fields.Boolean(
        'Auto-resuelto', default=False, readonly=True,
        help='True si este registro fue creado automáticamente por el '
             'sistema al encontrar un OACI desconocido.')

    notas = fields.Text()

    _sql_constraints = [
        ('icao_uniq', 'UNIQUE(icao)', 'Ya existe un mapeo para este OACI.'),
    ]

    # ---------- API pública ----------

    @api.model
    def resolve(self, icao):
        """Devuelve dict de resolución para icao, auto-creando el registro si no existe."""
        if not icao:
            return None
        icao_up = icao.upper().strip()
        rec = self.search([('icao', '=', icao_up)], limit=1)
        if not rec:
            rec = self._auto_resolve(icao_up)
        if not rec:
            return None

        ref_entry = {
            'station_code': rec.station_code or None,
            'station_nombre': rec.station_nombre or None,
            'station_distancia_km': rec.station_distancia_km or None,
            'ref_distancia_km': rec.ref_distancia_km or None,
        }

        if not rec.tiene_metar_propio and rec.ref_icao:
            return {
                'icao_consultar': rec.ref_icao.upper(),
                'fir': rec.fir,
                'usa_referencia': True,
                'nombre': rec.nombre,
                'ref_nombre': rec.ref_nombre or rec.ref_icao,
                'proveedor_oficial': rec.proveedor_oficial or 'aemet',
                **ref_entry,
            }
        return {
            'icao_consultar': rec.icao,
            'fir': rec.fir,
            'usa_referencia': False,
            'nombre': rec.nombre,
            'ref_nombre': None,
            'proveedor_oficial': rec.proveedor_oficial or 'aemet',
            **ref_entry,
        }

    # ---------- Auto-resolución ----------

    @api.model
    def _auto_resolve(self, icao):
        """Intenta crear un registro para icao consultando OpenAIP + CheckWX + AEMET."""
        from .leulit_meteo_openaip_service import OpenAIPService
        from .leulit_meteo_checkwx_service import CheckWXService
        from .leulit_meteo_aemet_service import AemetOpenDataService

        ICP = self.env['ir.config_parameter'].sudo()
        openaip_key = ICP.get_param('leulit_meteo.openaip_api_key', '')
        checkwx_key = ICP.get_param('leulit_meteo.checkwx_api_key', '')
        aemet_key = ICP.get_param('leulit_meteo.aemet_api_key', '')

        # 1. Coordenadas del OACI via OpenAIP
        airport_info = None
        lat = lon = None
        if openaip_key:
            airport_info = OpenAIPService.get_airport_by_icao(icao, openaip_key)
            if airport_info:
                lat = airport_info.get('lat')
                lon = airport_info.get('lon')

        # 2. ¿El propio OACI tiene METAR en CheckWX?
        ref_icao = None
        ref_nombre = None
        ref_dist_km = 0.0
        proveedor = 'aemet'
        tiene_metar = False
        station_info = None

        if checkwx_key:
            station_info = CheckWXService.get_station(icao, checkwx_key)
            if station_info:
                # Rellenar coordenadas si OpenAIP no las dio
                if lat is None:
                    lat = station_info.get('lat')
                    lon = station_info.get('lon')
                # Verificar si realmente tiene METAR
                test_metar = CheckWXService.get_metar(icao, checkwx_key)
                if test_metar:
                    tiene_metar = True
                    ref_icao = icao
                    ref_nombre = station_info.get('name', icao)
                    ref_dist_km = 0.0
                    country = station_info.get('country_code', '')
                    proveedor = 'aemet' if country == 'ES' else 'checkwx'

        # 3. Si no tiene METAR propio → buscar aeródromo con METAR cercano
        if not tiene_metar and lat is not None and checkwx_key and openaip_key:
            nearby = OpenAIPService.get_airports_near(
                lat, lon, _SEARCH_RADIUS_KM, openaip_key, limit=15)
            for candidate in nearby:
                cand_icao = candidate.get('icao', '')
                if not cand_icao or cand_icao == icao:
                    continue
                cand_metar = CheckWXService.get_metar(cand_icao, checkwx_key)
                if cand_metar:
                    cand_station = CheckWXService.get_station(cand_icao, checkwx_key)
                    ref_icao = cand_icao
                    ref_nombre = (cand_station.get('name') if cand_station else None) or candidate.get('name') or cand_icao
                    ref_dist_km = candidate.get('dist_km', 0.0)
                    country = (cand_station.get('country_code', '') if cand_station else '')
                    proveedor = 'aemet' if country == 'ES' else 'checkwx'
                    break

        # 4. FIR por heurística (el registro en tabla se gestiona en resolve())
        fir = _fir_heuristic(lat, lon)

        # 5. Estación AEMET más próxima (solo si tenemos coordenadas)
        station_code = None
        station_nombre_str = None
        station_dist = None
        if lat is not None and aemet_key:
            inventario = AemetOpenDataService.get_inventario_estaciones(aemet_key)
            if inventario:
                nearest, dist_km = AemetOpenDataService.find_nearest_station(
                    lat, lon, inventario)
                if nearest:
                    station_code = nearest.get('indicativo')
                    station_nombre_str = nearest.get('nombre')
                    station_dist = dist_km

        # 6. Determinar nombre del punto
        nombre = (airport_info.get('name') if airport_info else None) or \
                 (station_info.get('name') if station_info else None) or icao

        # 7. Crear registro
        vals = {
            'icao': icao,
            'nombre': nombre,
            'fir': fir,
            'tiene_metar_propio': tiene_metar,
            'ref_icao': ref_icao if not tiene_metar else None,
            'ref_nombre': ref_nombre if not tiene_metar else None,
            'ref_distancia_km': ref_dist_km if not tiene_metar else 0.0,
            'latitud': lat or 0.0,
            'longitud': lon or 0.0,
            'station_code': station_code,
            'station_nombre': station_nombre_str,
            'station_distancia_km': station_dist or 0.0,
            'proveedor_oficial': proveedor,
            'auto_resolved': True,
        }
        try:
            rec = self.sudo().with_context(no_recompute=True).create(vals)
            _logger.info(
                "leulit.meteo.icao.reference: auto-resuelto %s -> ref=%s fir=%s",
                icao, ref_icao or 'propio', fir)
            return rec
        except Exception as exc:
            # Concurrencia: otro hilo ya lo creó
            _logger.warning(
                "Auto-resolve %s: no se pudo crear registro (%s). "
                "Reintentando búsqueda.", icao, exc)
            return self.search([('icao', '=', icao)], limit=1) or None

    @api.model
    def _enrich_ref_icao(self, icao):
        """Busca el aeródromo MET más próximo y actualiza el registro cuando AEMET no tiene datos.

        Se llama desde el proveedor cuando AEMET no devuelve METAR/TAF para un OACI
        (registro existente pero marcado incorrectamente como tiene_metar_propio=True,
        o sin ref_icao configurado). Usa OpenAIP para coordenadas y CheckWX para
        encontrar el aeródromo con METAR oficial más cercano.

        Returns dict con ref_icao, ref_nombre, proveedor_oficial; o None si falla.
        """
        from .leulit_meteo_openaip_service import OpenAIPService
        from .leulit_meteo_checkwx_service import CheckWXService
        from .leulit_meteo_aemet_service import AemetOpenDataService

        ICP = self.env['ir.config_parameter'].sudo()
        openaip_key = ICP.get_param('leulit_meteo.openaip_api_key', '')
        checkwx_key = ICP.get_param('leulit_meteo.checkwx_api_key', '')
        aemet_key = ICP.get_param('leulit_meteo.aemet_api_key', '')

        rec = self.search([('icao', '=', icao)], limit=1)
        _logger.info(
            "_enrich_ref_icao %s: rec=%s openaip_key=%s checkwx_key=%s aemet_key=%s",
            icao, bool(rec), bool(openaip_key), bool(checkwx_key), bool(aemet_key))
        if not rec:
            return None

        lat = rec.latitud if rec.latitud else None
        lon = rec.longitud if rec.longitud else None
        _logger.info("_enrich_ref_icao %s: coords en registro → lat=%s lon=%s", icao, lat, lon)

        # Coordenadas del OACI via OpenAIP si no están en el registro
        if not lat and openaip_key:
            airport_info = OpenAIPService.get_airport_by_icao(icao, openaip_key)
            _logger.info("_enrich_ref_icao %s: OpenAIP → %s", icao, airport_info)
            if airport_info:
                lat = airport_info.get('lat')
                lon = airport_info.get('lon')

        if not lat:
            _logger.warning("_enrich_ref_icao %s: no se obtuvieron coordenadas (openaip_key=%s)", icao, bool(openaip_key))
            return None

        # Buscar el aeródromo con METAR oficial más próximo
        ref_icao = None
        ref_nombre = None
        ref_dist_km = 0.0
        proveedor = 'aemet'

        if checkwx_key and openaip_key:
            nearby = OpenAIPService.get_airports_near(
                lat, lon, _SEARCH_RADIUS_KM, openaip_key, limit=15)
            _logger.info(
                "_enrich_ref_icao %s: OpenAIP nearby (%.0fkm) → %d candidatos",
                icao, _SEARCH_RADIUS_KM, len(nearby) if nearby else 0)
            for candidate in nearby:
                cand_icao = candidate.get('icao', '')
                if not cand_icao or cand_icao == icao:
                    continue
                cand_metar = CheckWXService.get_metar(cand_icao, checkwx_key)
                _logger.info(
                    "_enrich_ref_icao %s: CheckWX METAR para %s → %s",
                    icao, cand_icao, bool(cand_metar))
                if cand_metar:
                    cand_station = CheckWXService.get_station(cand_icao, checkwx_key)
                    ref_icao = cand_icao
                    ref_nombre = (
                        (cand_station.get('name') if cand_station else None)
                        or candidate.get('name') or cand_icao
                    )
                    ref_dist_km = candidate.get('dist_km', 0.0)
                    country = (cand_station.get('country_code', '') if cand_station else '')
                    proveedor = 'aemet' if country == 'ES' else 'checkwx'
                    break
        else:
            _logger.warning(
                "_enrich_ref_icao %s: sin checkwx_key o sin openaip_key, "
                "no se puede buscar aeródromo próximo", icao)

        if not ref_icao:
            _logger.warning(
                "_enrich_ref_icao %s: no se encontró aeródromo MET en %d km",
                icao, _SEARCH_RADIUS_KM)
            return None

        # Estación AEMET más próxima (si no estaba ya configurada)
        station_code = rec.station_code or None
        station_nombre = rec.station_nombre or None
        station_dist = rec.station_distancia_km or None

        if not station_code and lat and aemet_key:
            inventario = AemetOpenDataService.get_inventario_estaciones(aemet_key)
            if inventario:
                nearest, dist_km = AemetOpenDataService.find_nearest_station(
                    lat, lon, inventario)
                if nearest:
                    station_code = nearest.get('indicativo')
                    station_nombre = nearest.get('nombre')
                    station_dist = dist_km

        # Actualizar el registro para que la próxima consulta sea directa
        try:
            rec.sudo().write({
                'tiene_metar_propio': False,
                'ref_icao': ref_icao,
                'ref_nombre': ref_nombre,
                'ref_distancia_km': ref_dist_km,
                'latitud': lat,
                'longitud': lon or 0.0,
                'proveedor_oficial': proveedor,
                'station_code': station_code,
                'station_nombre': station_nombre,
                'station_distancia_km': station_dist or 0.0,
            })
            _logger.info(
                "_enrich_ref_icao: %s → ref=%s (%.1f km, proveedor=%s)",
                icao, ref_icao, ref_dist_km, proveedor)
        except Exception as exc:
            _logger.warning("_enrich_ref_icao %s: error al actualizar: %s", icao, exc)
            return None

        return {
            'ref_icao': ref_icao,
            'ref_nombre': ref_nombre,
            'ref_distancia_km': ref_dist_km,
            'proveedor_oficial': proveedor,
        }
