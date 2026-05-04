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
        elev = item.get('elevation', {})
        elev_val = elev.get('value') or 0
        elev_unit = (elev.get('unit') or 'FT').upper()
        elev_ft = int(float(elev_val) * 3.28084) if elev_unit == 'M' else int(float(elev_val))
        return {
            'icao': item.get('icaoCode') or '',
            'name': item.get('name') or '',
            'lat': float(coords[1]),
            'lon': float(coords[0]),
            'elevation_ft': elev_ft,
        }

    @classmethod
    def _match_icao_in_items(cls, items, icao_up):
        """Busca icao_up en una lista de ítems de la API. Devuelve parsed o None."""
        for item in items:
            parsed = cls._parse_airport(item)
            if not parsed:
                continue
            # Comprobar todos los campos donde OpenAIP puede guardar el ICAO
            for field in ('icaoCode', 'icao', 'oaci', 'code'):
                if (item.get(field) or '').upper() == icao_up:
                    parsed['icao'] = icao_up
                    return parsed
        return None

    @classmethod
    def get_airport_by_icao(cls, icao, api_key):
        """Devuelve {'icao', 'name', 'lat', 'lon'} o None.

        Estrategia:
        1. Filtro ?icaoCode= (la API puede ignorarlo y devolver ítems sin ICAO).
        2. Búsqueda ?search= si el filtro no devolvió match exacto.
        """
        if not icao or not api_key:
            return None
        icao_up = icao.upper().strip()
        try:
            # ── Intento 1: filtro icaoCode ───────────────────────────────────
            r = requests.get(
                f"{cls.BASE_URL}/airports",
                headers=cls._headers(api_key),
                params={"icaoCode": icao_up, "limit": 10},
                timeout=cls.TIMEOUT)
            if r.status_code == 200:
                items = r.json().get('items') or []
                result = cls._match_icao_in_items(items, icao_up)
                if result:
                    return result
                _logger.debug(
                    "OpenAIP ?icaoCode=%s: %d ítems sin match exacto", icao, len(items))

            # ── Intento 2: búsqueda por texto ────────────────────────────────
            r2 = requests.get(
                f"{cls.BASE_URL}/airports",
                headers=cls._headers(api_key),
                params={"search": icao_up, "limit": 10},
                timeout=cls.TIMEOUT)
            if r2.status_code == 200:
                items2 = r2.json().get('items') or []
                result = cls._match_icao_in_items(items2, icao_up)
                if result:
                    _logger.info(
                        "OpenAIP get_airport_by_icao(%s): encontrado via ?search=", icao)
                    return result

            _logger.warning(
                "OpenAIP get_airport_by_icao(%s): sin match en icaoCode ni search", icao)
            return None
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
