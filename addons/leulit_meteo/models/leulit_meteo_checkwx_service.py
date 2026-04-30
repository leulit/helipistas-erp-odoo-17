# -*- coding: utf-8 -*-
import logging
import requests

_logger = logging.getLogger(__name__)


class CheckWXService:
    BASE_URL = "https://api.checkwx.com"
    TIMEOUT = 15

    @classmethod
    def _headers(cls, api_key):
        return {"X-API-KEY": api_key, "Accept": "application/json"}

    @classmethod
    def _get(cls, path, api_key):
        if not api_key:
            return None
        try:
            r = requests.get(
                f"{cls.BASE_URL}{path}",
                headers=cls._headers(api_key),
                timeout=cls.TIMEOUT)
            if r.status_code == 404:
                return None
            if r.status_code == 401:
                _logger.error("CheckWX %s -> HTTP 401 (API Key inválida o sin permisos)", path)
                return None
            if r.status_code != 200:
                _logger.warning("CheckWX %s -> HTTP %s: %s", path, r.status_code, r.text[:200])
                return None
            return r.json()
        except Exception as exc:
            _logger.error("CheckWX %s: %s", path, exc)
            return None

    @classmethod
    def get_metar(cls, icao, api_key):
        """Devuelve el texto RAW del METAR o None."""
        data = cls._get(f"/v2/metar/{icao.upper()}", api_key)
        if not data or not data.get('data'):
            return None
        items = data['data']
        return items[0] if isinstance(items[0], str) else items[0].get('raw_text')

    @classmethod
    def get_taf(cls, icao, api_key):
        """Devuelve el texto RAW del TAF o None."""
        data = cls._get(f"/v2/taf/{icao.upper()}", api_key)
        if not data or not data.get('data'):
            return None
        items = data['data']
        return items[0] if isinstance(items[0], str) else items[0].get('raw_text')

    @classmethod
    def get_station(cls, icao, api_key):
        """Devuelve {'icao', 'name', 'lat', 'lon', 'country_code'} o None."""
        data = cls._get(f"/v2/station/{icao.upper()}", api_key)
        if not data or not data.get('data'):
            return None
        item = data['data'][0]
        coords = item.get('geometry', {}).get('coordinates')
        lat = item.get('latitude', {}).get('decimal')
        lon = item.get('longitude', {}).get('decimal')
        if coords and len(coords) >= 2:
            lon = float(coords[0])
            lat = float(coords[1])
        if lat is None or lon is None:
            return None
        elev = item.get('elevation', {})
        return {
            'icao': item.get('icao', icao).upper(),
            'name': item.get('name', ''),
            'lat': float(lat),
            'lon': float(lon),
            'country_code': item.get('country', {}).get('code', ''),
            'elevation_ft': int(elev.get('feet') or 0) if elev else 0,
        }

    @classmethod
    def get_nearest_metar(cls, lat, lon, radius_nm, api_key):
        """Devuelve lista de {'icao','name','lat','lon','country_code'} con METAR en el radio.

        Usa /v2/metar/lat/{lat}/lon/{lon}/radius/{radius}/decoded.
        radius_nm en millas náuticas (150 km ≈ 81 nm).
        """
        data = cls._get(
            f"/v2/metar/lat/{lat}/lon/{lon}/radius/{int(radius_nm)}/decoded",
            api_key)
        if not data or not data.get('data'):
            return []
        results = []
        for item in data['data']:
            icao = item.get('icao', '')
            if not icao:
                continue
            station = item.get('station', {})
            coords = station.get('geometry', {}).get('coordinates')
            slat = station.get('latitude', {}).get('decimal')
            slon = station.get('longitude', {}).get('decimal')
            if coords and len(coords) >= 2:
                slon = float(coords[0])
                slat = float(coords[1])
            if slat is None or slon is None:
                continue
            selev = station.get('elevation', {})
            results.append({
                'icao': icao.upper(),
                'name': station.get('name', ''),
                'lat': float(slat),
                'lon': float(slon),
                'country_code': station.get('country', {}).get('code', ''),
                'elevation_ft': int(selev.get('feet') or 0) if selev else 0,
            })
        return results

    @classmethod
    def get_stations_by_country(cls, country_code, api_key):
        """Devuelve lista de {'icao','name','lat','lon','country_code'} de un país.

        Usa /v2/station/country/{code}. Devuelve todas las estaciones registradas
        independientemente de si tienen METAR activo en este momento.
        """
        data = cls._get(f"/v2/station/country/{country_code.upper()}", api_key)
        if not data or not data.get('data'):
            _logger.warning(
                "CheckWX get_stations_by_country(%s): sin datos (data=%s)",
                country_code, bool(data))
            return []
        raw_items = data['data']
        _logger.info(
            "CheckWX get_stations_by_country(%s): %d estaciones recibidas de la API",
            country_code, len(raw_items))
        results = []
        sin_coords = 0
        for item in raw_items:
            icao = (item.get('icao') or '').upper().strip()
            if not icao:
                continue
            coords = item.get('geometry', {}).get('coordinates')
            lat = item.get('latitude', {}).get('decimal')
            lon = item.get('longitude', {}).get('decimal')
            if coords and len(coords) >= 2:
                lon = float(coords[0])
                lat = float(coords[1])
            if lat is None or lon is None:
                sin_coords += 1
                continue
            ielev = item.get('elevation', {})
            results.append({
                'icao': icao,
                'name': item.get('name', ''),
                'lat': float(lat),
                'lon': float(lon),
                'country_code': item.get('country', {}).get('code', ''),
                'elevation_ft': int(ielev.get('feet') or 0) if ielev else 0,
            })
        if sin_coords:
            _logger.debug(
                "CheckWX get_stations_by_country(%s): %d estaciones descartadas por falta de coords",
                country_code, sin_coords)
        _logger.info(
            "CheckWX get_stations_by_country(%s): %d estaciones con coords válidas",
            country_code, len(results))
        return results

    @classmethod
    def validate_api_key(cls, api_key):
        data = cls._get("/v2/station/LEMD", api_key)
        return data is not None
