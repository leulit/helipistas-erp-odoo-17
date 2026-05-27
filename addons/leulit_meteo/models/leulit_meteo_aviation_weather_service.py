# -*- coding: utf-8 -*-
import csv
import logging
import os

import requests

_logger = logging.getLogger(__name__)

_BASE_URL = "https://aviationweather.gov/api/data"
_TIMEOUT = 30
_SEED_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'aerodromos_es_seed.csv'
)


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
        """Estaciones españolas con servicio METAR o TAF.

        Fuentes:
        1. Seed CSV local curado desde AIP España (ENAIRE): lista oficial de
           aeródromos con coordenadas verificadas contra OPMET WMO (NOAA).
        2. NOAA /api/data/metar y /api/data/taf con todos los ICAOs en batch
           para marcar disponibilidad real de METAR/TAF.

        Devuelve dict {icao: {'nombre', 'lat', 'lon', 'has_metar', 'has_taf',
        'elevation_ft'}} incluyendo TODOS los del seed. Si NOAA falla por
        problemas de red, devuelve el seed completo con has_metar=True y
        has_taf=True (mejor mantener funcionalidad que perder estaciones por
        fallo transitorio).
        """
        seed = cls._load_seed()
        if not seed:
            _logger.warning(
                "AviationWeather: seed vacío o no encontrado en %s", _SEED_PATH
            )
            return {}

        ids_str = ','.join(sorted(seed.keys()))
        metar_set = cls._query_noaa_ids('metar', ids_str)
        taf_set = cls._query_noaa_ids('taf', ids_str)

        noaa_vacio = not metar_set and not taf_set
        if noaa_vacio:
            _logger.warning(
                "AviationWeather: NOAA no devolvió datos (fallo de red?). "
                "Usando seed completo con has_metar=True, has_taf=True."
            )

        result = {}
        for icao, info in seed.items():
            result[icao] = {
                'nombre': info['nombre'],
                'lat': info['lat'],
                'lon': info['lon'],
                'elevation_ft': info['elevation_ft'],
                'has_metar': True if noaa_vacio else (icao in metar_set),
                'has_taf': True if noaa_vacio else (icao in taf_set),
            }

        _logger.info(
            "AviationWeather: %d estaciones en seed → %d con METAR / %d con TAF (NOAA).",
            len(seed),
            sum(1 for v in result.values() if v['has_metar']),
            sum(1 for v in result.values() if v['has_taf']),
        )
        return result

    @classmethod
    def _load_seed(cls):
        """Carga el seed CSV local. Devuelve dict {icao: {'nombre', 'lat', 'lon', 'elevation_ft'}}."""
        seed_path = os.path.normpath(_SEED_PATH)
        try:
            with open(seed_path, encoding='utf-8', newline='') as f:
                lines = [l for l in f if not l.startswith('#') and l.strip()]
            reader = csv.DictReader(lines)
            result = {}
            for row in reader:
                icao = (row.get('icao') or '').strip().upper()
                if not icao:
                    continue
                try:
                    lat = float(row.get('latitud') or 0)
                    lon = float(row.get('longitud') or 0)
                    elevation_ft = int(float(row.get('elevacion_ft') or 0))
                except (ValueError, TypeError):
                    lat, lon, elevation_ft = 0.0, 0.0, 0
                result[icao] = {
                    'nombre': (row.get('nombre') or icao).strip(),
                    'lat': lat,
                    'lon': lon,
                    'elevation_ft': elevation_ft,
                }
            return result
        except FileNotFoundError:
            _logger.error("AviationWeather: seed no encontrado en %s", seed_path)
            return {}
        except Exception as exc:
            _logger.error("AviationWeather: error leyendo seed: %s", exc)
            return {}

    @classmethod
    def _query_noaa_ids(cls, datasource, ids_str):
        """Consulta NOAA /api/data/{datasource} con lista de ICAOs. Devuelve set de ICAOs con datos."""
        try:
            r = requests.get(
                f"{_BASE_URL}/{datasource}",
                params={'ids': ids_str, 'format': 'json'},
                timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                _logger.warning("AviationWeather: NOAA %s → HTTP %s", datasource, r.status_code)
                return set()
            items = r.json()
            if not isinstance(items, list):
                return set()
            result = set()
            for item in items:
                icao = (item.get('icaoId') or item.get('stationId') or '').upper().strip()
                if icao:
                    result.add(icao)
            return result
        except Exception as exc:
            _logger.error("AviationWeather: error consultando NOAA %s: %s", datasource, exc)
            return set()

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
