# -*- coding: utf-8 -*-
import logging
import math
import requests

_logger = logging.getLogger(__name__)


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class OpenAIPService:
    BASE_URL = "https://api.core.openaip.net/api"
    TIMEOUT = 15

    @classmethod
    def _headers(cls, api_key):
        return {"x-openaip-api-key": api_key, "Accept": "application/json"}

    @classmethod
    def _parse_airport(cls, item):
        coords = item.get('geometry', {}).get('coordinates')
        if not coords or len(coords) < 2:
            return None
        return {
            'icao': item.get('icaoCode') or '',
            'name': item.get('name') or '',
            'lat': float(coords[1]),
            'lon': float(coords[0]),
        }

    @classmethod
    def get_airport_by_icao(cls, icao, api_key):
        """Devuelve {'icao', 'name', 'lat', 'lon'} o None."""
        if not icao or not api_key:
            return None
        try:
            r = requests.get(
                f"{cls.BASE_URL}/airports",
                headers=cls._headers(api_key),
                params={"icaoCode": icao.upper().strip(), "limit": 1},
                timeout=cls.TIMEOUT)
            if r.status_code != 200:
                _logger.warning("OpenAIP %s -> HTTP %s", icao, r.status_code)
                return None
            items = r.json().get('items') or []
            if not items:
                return None
            return cls._parse_airport(items[0])
        except Exception as exc:
            _logger.error("OpenAIP get_airport_by_icao(%s): %s", icao, exc)
            return None

    @classmethod
    def get_airports_near(cls, lat, lon, radius_km, api_key, limit=15):
        """Devuelve lista de {'icao', 'name', 'lat', 'lon', 'dist_km'} ordenada por distancia."""
        if not api_key:
            return []
        deg_lat = radius_km / 111.0
        deg_lon = radius_km / (111.0 * math.cos(math.radians(lat)))
        try:
            r = requests.get(
                f"{cls.BASE_URL}/airports",
                headers=cls._headers(api_key),
                params={
                    "page": 1,
                    "limit": 50,
                    "latMin": lat - deg_lat,
                    "latMax": lat + deg_lat,
                    "lonMin": lon - deg_lon,
                    "lonMax": lon + deg_lon,
                },
                timeout=cls.TIMEOUT)
            if r.status_code != 200:
                _logger.warning("OpenAIP near(%s,%s) -> HTTP %s", lat, lon, r.status_code)
                return []
            items = r.json().get('items') or []
        except Exception as exc:
            _logger.error("OpenAIP get_airports_near: %s", exc)
            return []

        results = []
        for item in items:
            parsed = cls._parse_airport(item)
            if not parsed or not parsed['icao']:
                continue
            dist = _haversine(lat, lon, parsed['lat'], parsed['lon'])
            if dist <= radius_km:
                parsed['dist_km'] = round(dist, 1)
                results.append(parsed)
        results.sort(key=lambda x: x['dist_km'])
        return results[:limit]
