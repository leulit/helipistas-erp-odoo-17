# -*- coding: utf-8 -*-
"""Parser ligero (best-effort) de mensajes METAR.

El RAW METAR es la fuente legal de verdad y NO se altera. Este parser
sólo extrae campos derivados habituales para mostrarlos en una tabla
decodificada en el formulario Odoo. Si algún campo no se puede extraer
devuelve ``None`` y el flujo continúa.

Campos que intenta extraer:
    * observation_time  (DDHHMMZ -> datetime UTC, naive)
    * wind_direction    (grados)
    * wind_speed_kt     (nudos)
    * wind_gust_kt      (nudos, opcional)
    * visibility_m      (metros; ``9999`` se mapea a 9999)
    * temperatura       (°C; prefijo ``M`` -> negativo)
    * dewpoint          (°C)
    * qnh               (hPa; ``Q####`` directo, ``A####`` -> conversión)
"""

import logging
import re
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)


# El primer "token" útil tras el ICAO es la fecha/hora DDHHMMZ.
_RE_OBS_TIME = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")
# Viento DDDFFKT, DDDFFGGGKT, VRBFFKT, VRBFFGGGKT (KT/MPS/KMH)
_RE_WIND = re.compile(
    r"\b(?P<dir>\d{3}|VRB)(?P<spd>\d{2,3})"
    r"(?:G(?P<gst>\d{2,3}))?(?P<unit>KT|MPS|KMH)\b"
)
# Visibilidad: 9999 o 4 dígitos. Ojo: hay que aplicarla DESPUÉS del bloque
# de viento (el viento ya consume sus dígitos, así que un \b\d{4}\b sin más
# capturaría la hora si la pusiéramos antes; por eso eliminamos la hora
# antes de buscar visibilidad).
_RE_VIS_4 = re.compile(r"\b(\d{4})\b")
# Temperatura/punto de rocío  TT/DD  con M para negativos.
_RE_TT_DD = re.compile(
    r"\b(M?\d{2})/(M?\d{2})\b"
)
# QNH en hPa: Q####
_RE_QNH_Q = re.compile(r"\bQ(\d{4})\b")
# QNH en inHg: A#### (inHg * 100). 2992 inHg -> 1013.25 hPa.
_RE_QNH_A = re.compile(r"\bA(\d{4})\b")

# Conversiones
_KMH_TO_KT = 0.5399568
_MPS_TO_KT = 1.943844
_INHG_TO_HPA = 33.8639  # 1 inHg ~ 33.8639 hPa


def _parse_temp(token):
    """`'M05'` -> -5.0; `'12'` -> 12.0; otra cosa -> None."""
    if not token:
        return None
    try:
        if token.startswith('M'):
            return -float(token[1:])
        return float(token)
    except ValueError:
        return None


def _parse_obs_time(text, now=None):
    """Devuelve datetime UTC (naive) tomando DDHHMMZ del METAR.

    Como el METAR no lleva año/mes, los inferimos del ``now`` actual:
    asumimos el mes/año actual; si el día del mensaje es mayor al de hoy
    en más de 5 días, asumimos mes anterior (ej. mensaje del día 30
    consultado el 1).
    """
    m = _RE_OBS_TIME.search(text)
    if not m:
        return None
    day, hour, minute = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    now = now or datetime.now(timezone.utc)
    year, month = now.year, now.month
    if day - now.day > 5:
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    try:
        dt = datetime(year, month, day, hour, minute, 0,
                      tzinfo=timezone.utc)
    except ValueError:
        return None
    return dt.replace(tzinfo=None)


def _parse_wind(text):
    m = _RE_WIND.search(text)
    if not m:
        return (None, None, None)
    direction = m.group('dir')
    speed = int(m.group('spd'))
    gust = m.group('gst')
    unit = m.group('unit')
    factor = {'KT': 1.0, 'MPS': _MPS_TO_KT, 'KMH': _KMH_TO_KT}[unit]
    spd_kt = round(speed * factor, 1)
    gst_kt = round(int(gust) * factor, 1) if gust else None
    if direction == 'VRB':
        return (None, spd_kt, gst_kt)
    return (int(direction), spd_kt, gst_kt)


def _parse_visibility(text_after_wind):
    """Busca el primer 4-dígitos como visibilidad en metros.

    Recibe el texto tras eliminar la hora y el viento (para evitar
    confusiones). ``9999`` se devuelve tal cual (= "10 km o más").
    """
    m = _RE_VIS_4.search(text_after_wind)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _parse_qnh(text):
    m = _RE_QNH_Q.search(text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    m = _RE_QNH_A.search(text)
    if m:
        try:
            inhg100 = int(m.group(1))  # 2992 = 29.92 inHg
            return round((inhg100 / 100.0) * _INHG_TO_HPA, 1)
        except ValueError:
            return None
    return None


def parse_metar(raw_metar, now=None):
    """Devuelve dict con campos derivados (best-effort) o {} si vacío.

    Nunca lanza excepciones: campos no detectados quedan a ``None``.
    """
    result = {
        'observation_time': None,
        'temperatura': None,
        'dewpoint': None,
        'wind_direction': None,
        'wind_speed_kt': None,
        'wind_gust_kt': None,
        'visibility_m': None,
        'qnh': None,
    }
    if not raw_metar:
        return result
    text = raw_metar.replace('\n', ' ').replace('\r', ' ').strip()
    if not text:
        return result

    try:
        result['observation_time'] = _parse_obs_time(text, now=now)

        wind_dir, wind_spd, wind_gst = _parse_wind(text)
        result['wind_direction'] = wind_dir
        result['wind_speed_kt'] = wind_spd
        result['wind_gust_kt'] = wind_gst

        # Limpiamos hora y viento para evitar que su 4 dígitos confunda
        # la búsqueda de visibilidad.
        text_clean = _RE_OBS_TIME.sub(' ', text)
        text_clean = _RE_WIND.sub(' ', text_clean)
        result['visibility_m'] = _parse_visibility(text_clean)

        m = _RE_TT_DD.search(text_clean)
        if m:
            result['temperatura'] = _parse_temp(m.group(1))
            result['dewpoint'] = _parse_temp(m.group(2))

        result['qnh'] = _parse_qnh(text_clean)
    except Exception as exc:  # noqa: BLE001
        # Best-effort: no podemos romper el flujo por un parseo.
        _logger.debug("parse_metar fallo silencioso: %s", exc)

    return result
