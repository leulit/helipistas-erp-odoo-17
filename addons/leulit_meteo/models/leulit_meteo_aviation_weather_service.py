# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET

import requests

_BASE_URL = "https://aviationweather.gov/api/data"
_ADDS_URL = "https://www.aviationweather.gov/adds/dataserver_current/httpparam"
_TIMEOUT = 30


class AviationWeatherService:
    """Cliente para la API pública de aviationweather.gov (NOAA/FAA).

    No requiere API key. Devuelve METAR y TAF en formato RAW.
    Documentación: https://aviationweather.gov/data/api/
    """

    @classmethod
    def get_metar(cls, icao):
        """Devuelve el texto RAW del METAR más reciente o None."""
        try:
            r = requests.get(
                f"{_BASE_URL}/metar",
                params={'ids': icao.upper(), 'format': 'raw'},
                timeout=_TIMEOUT)
            if r.status_code != 200:
                return None
            text = r.text.strip()
            return text if text else None
        except Exception:
            return None

    @classmethod
    def get_taf(cls, icao):
        """Devuelve el texto RAW del TAF más reciente o None."""
        try:
            r = requests.get(
                f"{_BASE_URL}/taf",
                params={'ids': icao.upper(), 'format': 'raw'},
                timeout=_TIMEOUT)
            if r.status_code != 200:
                return None
            text = r.text.strip()
            return text if text else None
        except Exception:
            return None

    @classmethod
    def get_stations_spain(cls):
        """Estaciones españolas (LE*, GC*) que tienen METAR o TAF.

        Combina dos fuentes de aviationweather.gov (sin API key):
        1. ADDS station database (estaciones registradas con flags METAR/TAF)
        2. Observaciones METAR/TAF reales (detecta estaciones activas no registradas en el ADDS,
           por ejemplo LELL que tiene METAR pero no aparece en el station database)
        Fallback: bounding-box si ambas fuentes fallan.
        Devuelve dict {icao: {'nombre', 'lat', 'lon', 'has_metar', 'has_taf', 'elevation_ft'}}.
        """
        result = cls._get_stations_adds()

        obs = cls._get_stations_from_metars()
        nuevas = {icao: info for icao, info in obs.items() if icao not in result}
        if nuevas:
            _logger.info(
                "AviationWeather: %d estación(es) adicional(es) vía observaciones METAR/TAF: %s",
                len(nuevas), ', '.join(sorted(nuevas.keys())))
            result.update(nuevas)

        if not result:
            result = cls._get_stations_bbox()
        return result

    @classmethod
    def _get_stations_from_metars(cls):
        """Descubre estaciones activas consultando observaciones METAR/TAF reales.

        Complementa _get_stations_adds() encontrando aeródromos que emiten METAR o TAF
        pero no están registrados en la base de datos de estaciones ADDS.
        """
        result = {}
        for prefix in ('LE', 'GC'):
            for datasource, flag in (('metars', 'has_metar'), ('tafs', 'has_taf')):
                hours = '2' if datasource == 'metars' else '24'
                tag = 'METAR' if datasource == 'metars' else 'TAF'
                try:
                    r = requests.get(
                        _ADDS_URL,
                        params={
                            'dataSource': datasource,
                            'requestType': 'retrieve',
                            'format': 'xml',
                            'stationString': f'{prefix}*',
                            'hoursBeforeNow': hours,
                            'mostRecentForEachStation': 'constraint',
                        },
                        timeout=_TIMEOUT,
                    )
                    if r.status_code != 200:
                        _logger.warning("stations_from_%s %s* -> HTTP %s", datasource, prefix, r.status_code)
                        continue
                    root = ET.fromstring(r.content)
                    data_el = root.find('data')
                    if data_el is None:
                        continue
                    for obs in data_el.findall(tag):
                        icao = (obs.findtext('station_id') or '').upper().strip()
                        if not icao:
                            continue
                        lat = float(obs.findtext('latitude') or 0)
                        lon = float(obs.findtext('longitude') or 0)
                        elev_m = float(obs.findtext('elevation_m') or 0)
                        entry = result.setdefault(icao, {
                            'nombre': icao,
                            'lat': lat,
                            'lon': lon,
                            'has_metar': False,
                            'has_taf': False,
                            'elevation_ft': int(elev_m * 3.28084),
                        })
                        entry[flag] = True
                except Exception as exc:
                    _logger.error("stations_from_%s %s*: %s", datasource, prefix, exc)
        return result

    @classmethod
    def _get_stations_adds(cls):
        """ADDS dataserver_current con stationString=LE*,GC* (XML station2_0)."""
        result = {}
        for prefix in ('LE', 'GC'):
            try:
                r = requests.get(
                    _ADDS_URL,
                    params={
                        'dataSource': 'stations',
                        'requestType': 'retrieve',
                        'format': 'xml',
                        'stationString': f'{prefix}*',
                    },
                    timeout=_TIMEOUT,
                )
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                data_el = root.find('data')
                if data_el is None:
                    continue
                for st in data_el.findall('Station'):
                    site_type = st.find('site_type')
                    has_metar = site_type is not None and site_type.find('METAR') is not None
                    has_taf = site_type is not None and site_type.find('TAF') is not None
                    if not (has_metar or has_taf):
                        continue
                    icao = (st.findtext('station_id') or '').upper().strip()
                    if not icao:
                        continue
                    elev_m = float(st.findtext('elevation_m') or 0)
                    result[icao] = {
                        'nombre': (st.findtext('site') or icao).strip(),
                        'lat': float(st.findtext('latitude') or 0),
                        'lon': float(st.findtext('longitude') or 0),
                        'has_metar': has_metar,
                        'has_taf': has_taf,
                        'elevation_ft': int(elev_m * 3.28084),
                    }
            except Exception:
                pass
        return result

    @classmethod
    def _get_stations_bbox(cls):
        """Fallback: bbox sobre Peninsula+Baleares y Canarias usando el API nuevo."""
        result = {}
        bboxes = [
            (35.0, -10.0, 44.5, 5.0),    # Peninsula + Baleares (minLat, minLon, maxLat, maxLon)
            (27.0, -18.5, 30.0, -13.0),  # Canarias
        ]
        for bbox in bboxes:
            for datasource in ('metar', 'taf'):
                try:
                    r = requests.get(
                        f"{_BASE_URL}/{datasource}",
                        params={
                            'bbox': ','.join(str(v) for v in bbox),
                            'format': 'json',
                        },
                        timeout=_TIMEOUT,
                    )
                    if r.status_code != 200:
                        continue
                    items = r.json() if isinstance(r.json(), list) else []
                    for item in items:
                        icao = (item.get('icaoId') or item.get('stationId') or '').upper().strip()
                        if not icao or not (icao.startswith('LE') or icao.startswith('GC')):
                            continue
                        entry = result.setdefault(icao, {
                            'nombre': item.get('name', icao).strip(),
                            'lat': float(item.get('lat') or item.get('latitude') or 0),
                            'lon': float(item.get('lon') or item.get('longitude') or 0),
                            'has_metar': False,
                            'has_taf': False,
                        })
                        entry[f'has_{datasource}'] = True
                except Exception:
                    pass
        return result

    @classmethod
    def validate(cls):
        """Comprueba que el servicio responde. Devuelve True si hay conectividad."""
        try:
            r = requests.get(
                f"{_BASE_URL}/metar",
                params={'ids': 'LEMD', 'format': 'raw'},
                timeout=_TIMEOUT)
            return r.status_code == 200
        except Exception:
            return False
