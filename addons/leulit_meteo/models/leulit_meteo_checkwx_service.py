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
            if r.status_code != 200:
                _logger.warning("CheckWX %s -> HTTP %s", path, r.status_code)
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
        return {
            'icao': item.get('icao', icao).upper(),
            'name': item.get('name', ''),
            'lat': float(lat),
            'lon': float(lon),
            'country_code': item.get('country', {}).get('code', ''),
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
            results.append({
                'icao': icao.upper(),
                'name': station.get('name', ''),
                'lat': float(slat),
                'lon': float(slon),
                'country_code': station.get('country', {}).get('code', ''),
            })
        return results

    @classmethod
    def validate_api_key(cls, api_key):
        data = cls._get("/v2/station/LEMD", api_key)
        return data is not None
