# -*- coding: utf-8 -*-
"""Capa de abstracción de proveedores METAR.

El modelo ``leulit.meteo.metar`` no conoce a ninguna API concreta: pide al
proveedor activo una observación normalizada y la guarda. Para añadir un
proveedor nuevo basta con crear un fichero que defina una subclase de
:class:`MetarProvider` decorada con :func:`register_provider` e importarlo
en ``models/__init__.py``.

Esquema normalizado que devuelve ``get_observation``:

    {
        'provider': 'aemet',                    # str (código del proveedor)
        'icao': 'LEMD' | None,                  # str OACI 4 letras
        'station_code': '3195' | None,          # str id estación del proveedor
        'station_name': 'MADRID, ...' | None,
        'observation_time': datetime UTC | None,
        'temperatura': 12.5 | None,             # °C
        'dewpoint': 8.0 | None,                 # °C
        'humidity': 70.0 | None,                # %
        'wind_direction': 280 | None,           # ° (0-360)
        'wind_speed_kt': 10.0 | None,           # nudos
        'wind_gust_kt': 15.0 | None,            # nudos
        'visibility_m': 10000 | None,           # metros
        'qnh': 1015.5 | None,                   # hPa (presión a nivel del mar)
        'pressure': 1013.0 | None,              # hPa (presión estación)
        'precipitation': 0.0 | None,            # mm
        'latitude': 40.47 | None,
        'longitude': -3.56 | None,
        'elevation': 609.0 | None,              # metros
        'raw_metar': 'LEMD ... RMK AEMET',      # str (puede ser sintético)
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
    """Devuelve la lista ``[(code, label), ...]`` para un Selection field."""
    return [(p.code, p.label) for p in _PROVIDERS.values()]


class MetarProvider(abc.ABC):
    """Interfaz que debe implementar cada proveedor de datos METAR."""

    #: Identificador corto del proveedor (ej. 'aemet'). Obligatorio.
    code = ''
    #: Etiqueta legible para mostrar en la UI.
    label = ''

    @abc.abstractmethod
    def get_observation(self, env, icao_code=None, station_code=None):
        """Devuelve un dict normalizado (ver módulo) o ``None``.

        El proveedor decide qué hacer si solo recibe ``icao_code`` o solo
        ``station_code``. Si la combinación no permite localizar una
        observación reciente, devuelve ``None``.
        """
        raise NotImplementedError

    def validate(self, env):
        """Comprueba que el proveedor está bien configurado.

        Por defecto devuelve ``True``. Sobrescribir en proveedores que
        requieran API key u otros recursos.
        """
        return True

    def prefill_station_code(self, icao_code):
        """Devuelve un ``station_code`` conocido para ese OACI o ``None``.

        Útil para mapear OACI a identificadores propios del proveedor sin
        llamar a la red. Por defecto, ``None``.
        """
        return None

    def coverage(self, icao_code):
        """Indica si este proveedor puede cubrir el OACI dado.

        Por defecto ``True``; cada proveedor puede afinarlo (p. ej. AEMET
        solo cubre prefijos LE/GC/GE).
        """
        return True
