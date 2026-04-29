# -*- coding: utf-8 -*-
import logging
import requests

_logger = logging.getLogger(__name__)

_BASE_URL = "https://aviationweather.gov/api/data"
_TIMEOUT = 15


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
                _logger.warning("AviationWeather METAR %s -> HTTP %s", icao, r.status_code)
                return None
            text = r.text.strip()
            return text if text else None
        except Exception as exc:
            _logger.error("AviationWeather METAR %s: %s", icao, exc)
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
                _logger.warning("AviationWeather TAF %s -> HTTP %s", icao, r.status_code)
                return None
            text = r.text.strip()
            return text if text else None
        except Exception as exc:
            _logger.error("AviationWeather TAF %s: %s", icao, exc)
            return None

    @classmethod
    def validate(cls):
        """Comprueba que el servicio responde. Devuelve True si hay conectividad."""
        try:
            r = requests.get(
                f"{_BASE_URL}/metar",
                params={'ids': 'LEMD', 'format': 'raw'},
                timeout=_TIMEOUT)
            return r.status_code == 200
        except Exception as exc:
            _logger.warning("AviationWeather validate: %s", exc)
            return False
