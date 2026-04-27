# -*- coding: utf-8 -*-
"""Capa de abstracción de proveedores METAR/TAF/SIGMET.

El modelo ``leulit.meteo.metar`` no conoce a ninguna API concreta: pide
al proveedor activo un briefing normalizado (METAR + TAF + SIGMET RAW
más campos derivados) y lo guarda. Para añadir un proveedor nuevo basta
con crear un fichero que defina una subclase de :class:`MetarProvider`
decorada con :func:`register_provider` e importarlo en
``models/__init__.py``.

Esquema normalizado que devuelve ``get_observation``:

    {
        'provider': 'aemet',
        'icao': 'LEUL',                 # OACI introducido por el usuario
        'icao_consultar': 'LELL',       # OACI realmente consultado
        'usa_referencia': True,         # se sustituyó por aeródromo ref
        'ref_icao': 'LELL' | None,
        'ref_nombre': 'Sabadell' | None,
        'fir_code': 'LECB' | None,
        'station_code': str | None,
        'station_name': str | None,
        'raw_metar': str | None,
        'raw_taf': str | None,
        'raw_sigmet': str | None,
        'observation_time': datetime UTC | None,
        'temperatura': 12.5 | None,             # °C  (parseado del METAR)
        'dewpoint': 8.0 | None,                 # °C
        'wind_direction': 280 | None,           # °
        'wind_speed_kt': 10.0 | None,           # nudos
        'wind_gust_kt': 15.0 | None,            # nudos
        'visibility_m': 10000 | None,           # metros
        'qnh': 1015.0 | None,                   # hPa
        'humidity': None, 'pressure': None,
        'precipitation': None, 'latitude': None,
        'longitude': None, 'elevation': None,   # legacy, hoy None
    }
"""

import abc
import logging

_logger = logging.getLogger(__name__)

#: Registro {code: instancia} de proveedores disponibles
_PROVIDERS = {}


def register_provider(cls):
    """Decorador para registrar una subclase de :class:`MetarProvider`."""
    instance = cls()
    if not instance.code:
        raise ValueError(
            f"Provider {cls.__name__} no tiene atributo 'code' definido")
    if instance.code in _PROVIDERS:
        _logger.warning("Provider METAR '%s' redefinido por %s",
                        instance.code, cls.__name__)
    _PROVIDERS[instance.code] = instance
    return cls


def get_provider(code):
    """Devuelve la instancia del proveedor o ``None`` si no existe."""
    return _PROVIDERS.get(code)


def all_providers():
    """Devuelve la lista de instancias registradas."""
    return list(_PROVIDERS.values())


def provider_selection():
    """Devuelve la lista ``[(code, label), ...]`` para un Selection."""
    return [(p.code, p.label) for p in _PROVIDERS.values()]


class MetarProvider(abc.ABC):
    """Interfaz que debe implementar cada proveedor de datos METAR."""

    #: Identificador corto del proveedor (ej. 'aemet'). Obligatorio.
    code = ''
    #: Etiqueta legible para mostrar en la UI.
    label = ''

    @abc.abstractmethod
    def get_observation(self, env, icao_code=None, station_code=None):
        """Devuelve un dict normalizado (ver módulo) o ``None``."""
        raise NotImplementedError

    def validate(self, env):
        """Comprueba que el proveedor está bien configurado.

        Por defecto devuelve ``True``. Sobrescribir en proveedores que
        requieran API key u otros recursos.
        """
        return True

    def resolve(self, env, icao_code):
        """Resuelve un OACI al ``station_code`` interno del proveedor.

        Devuelve ``None`` por defecto. Algunos proveedores podrán
        sobrescribirlo en el futuro si necesitan station_code.
        """
        return None
