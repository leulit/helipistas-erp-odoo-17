# -*- coding: utf-8 -*-
"""Cliente AEMET OpenData.

AEMET OpenData no expone METAR/TAF en su API pública (esos productos están
restringidos al servicio comercial AMA). Lo más parecido disponible son las
observaciones convencionales horarias de cada estación meteorológica
(``/api/observacion/convencional/datos/estacion/{idema}``). Muchas de esas
estaciones están ubicadas en aeropuertos/aeródromos, por lo que con sus
datos podemos construir un reporte de tipo METAR (sintético, no oficial)
con la última observación disponible.

Este servicio:
    * Encapsula el patrón de 2 llamadas de AEMET (endpoint -> URL ``datos``).
    * Resuelve un código OACI a un indicativo AEMET (IDEMA).
    * Devuelve la observación horaria más reciente normalizada.
    * Sintetiza un texto tipo METAR a partir de la observación.
"""

import json
import logging
import re
import requests
from datetime import datetime

_logger = logging.getLogger(__name__)


# Conversión de unidades
_MS_TO_KT = 1.943844  # m/s -> nudos


# Mapa estático OACI -> IDEMA para aeropuertos/aeródromos/helipuertos españoles
# de uso habitual. Si el aeródromo solicitado no está aquí, el usuario puede
# indicar el IDEMA directamente o se intentará resolver por nombre.
ICAO_TO_IDEMA = {
    # Aeropuertos peninsulares principales
    'LEMD': '3195',   # Madrid - Barajas
    'LEBL': '0076',   # Barcelona - El Prat
    'LEMG': '6155A',  # Málaga - Costa del Sol
    'LEAL': '8025',   # Alicante - Elche
    'LEVC': '8414A',  # Valencia
    'LEZL': '5783',   # Sevilla
    'LEBB': '1082',   # Bilbao
    'LEST': '1428',   # Santiago de Compostela
    'LEGE': '0367',   # Girona - Costa Brava
    'LERS': '0016A',  # Reus
    'LEZG': '9434',   # Zaragoza
    'LEVT': '9091O',  # Vitoria
    'LEPP': '9263D',  # Pamplona
    'LELN': '2661',   # León
    'LEAS': '1249I',  # Asturias
    'LECO': '1387',   # A Coruña
    'LEVX': '1495',   # Vigo
    'LESO': '1024E',  # San Sebastián
    'LEAB': '8175',   # Albacete
    'LEBZ': '4452',   # Badajoz
    'LEBG': '2331',   # Burgos
    'LEXJ': '1109',   # Santander
    'LEMH': 'B893',   # Menorca
    'LEPA': 'B228',   # Palma de Mallorca
    'LEIB': 'B954',   # Ibiza
    # Canarias
    'GCLP': 'C649I',  # Gran Canaria
    'GCXO': 'C447A',  # Tenerife Norte
    'GCTS': 'C429I',  # Tenerife Sur
    'GCFV': 'C249I',  # Fuerteventura
    'GCRR': 'C029O',  # Lanzarote
    'GCLA': 'C139E',  # La Palma
    'GCHI': 'C449C',  # El Hierro
    # Helipuertos / aeródromos pequeños habituales
    'LECU': '3194U',  # Cuatro Vientos
    'LETO': '3268C',  # Torrejón
    'LEGT': '3200',   # Getafe (referencia próxima Madrid)
    'LEMO': '5910',   # Morón (referencia)
    'LERO': '8019X',  # Logroño
    # Aeródromos / aeropuertos secundarios habituales
    # NOTA: algunos IDEMA son aproximaciones a estaciones cercanas. Verificar
    # con inventario AEMET. Si no se acierta, usar el buscador de estaciones.
    'LELL': '0149X',  # Sabadell - verificar con inventario AEMET
    'LEEC': '8412A',  # Murcia - San Javier (referencia próxima)
    'LERI': '7178I',  # San Javier (Murcia) - referencia
    'LECN': '5612X',  # Granada / Armilla - referencia
    'LEMI': '7031',   # Murcia (Alcantarilla) - referencia
    'LEAM': '6325O',  # Almería
    'LEJR': '5972X',  # Jerez
    # Los siguientes OACI no se mapean por falta de IDEMA fiable; usar el
    # buscador de estaciones AEMET desde la ficha del METAR:
    #   LECH (Castellón), LEMP (Empuriabrava), LEHC (Huesca),
    #   LERJ (La Rioja), LELC (La Cerdanya).
}


class AemetOpenDataService:
    """Cliente para la API AEMET OpenData."""

    BASE_URL = "https://opendata.aemet.es/opendata"
    TIMEOUT = 20

    # ---------- Llamadas básicas ----------

    @classmethod
    def _log_estado(cls, path, estado, descripcion):
        """Log unificado para los códigos de estado AEMET (HTTP o JSON)."""
        try:
            estado_int = int(estado) if estado is not None else None
        except (TypeError, ValueError):
            estado_int = None
        if estado_int == 401:
            _logger.warning(
                "AEMET %s -> 401 Unauthorized: API key inválida o no "
                "autorizada (%s)", path, descripcion)
        elif estado_int == 404:
            _logger.warning(
                "AEMET %s -> 404 Not Found: recurso/estación no encontrado "
                "(%s)", path, descripcion)
        elif estado_int == 429:
            _logger.warning(
                "AEMET %s -> 429 Too Many Requests: se ha excedido el "
                "límite de peticiones de la API. Reintenta más tarde (%s)",
                path, descripcion)
        else:
            _logger.error(
                "AEMET %s -> estado %s: %s", path, estado, descripcion)

    @classmethod
    def _request(cls, path, api_key, params=None):
        """Hace la primera llamada (devuelve la URL ``datos``).

        La autenticación AEMET se hace pasando ``api_key`` como **query
        parameter**, no como header. Es el patrón documentado por el
        Centro de Descargas de AEMET (ver ejemplo de curl en la web).

        Args:
            path: ruta del endpoint (debe empezar por ``/api/``)
            api_key: token de AEMET (JWT)
            params: query params adicionales

        Returns:
            dict con las claves ``datos`` y ``metadatos`` o ``None``.
        """
        if not api_key:
            _logger.error("AEMET API key no configurada")
            return None

        url = f"{cls.BASE_URL}{path}"
        headers = {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
        }
        # api_key SIEMPRE como query parameter (ver curl oficial AEMET)
        query = dict(params or {})
        query['api_key'] = api_key
        try:
            response = requests.get(url, headers=headers, params=query,
                                    timeout=cls.TIMEOUT)
            # Tratamos antes los códigos típicos para dar log específico
            status = response.status_code
            if status in (401, 404, 429):
                # Intentar extraer descripcion del JSON, si está
                descripcion = None
                try:
                    body = response.json()
                    descripcion = body.get('descripcion') if isinstance(
                        body, dict) else None
                except ValueError:
                    descripcion = response.text[:200]
                cls._log_estado(path, status, descripcion)
                return None
            response.raise_for_status()
            payload = response.json()
            estado = payload.get('estado') if isinstance(payload, dict) else None
            # Éxito: estado 200 o ausente (algunos endpoints no lo incluyen)
            if estado in (200, None):
                return payload
            # estado != 200 dentro del JSON: tratar igual que HTTP
            cls._log_estado(path, estado, payload.get('descripcion'))
            return None
        except requests.exceptions.RequestException as exc:
            _logger.error("Error llamando AEMET %s: %s", path, exc)
            return None
        except ValueError:
            _logger.error("Respuesta AEMET no JSON en %s", path)
            return None

    @classmethod
    def _decode_response(cls, response):
        """Decodifica el cuerpo de una respuesta AEMET probando varios
        encodings habituales (utf-8, iso-8859-15, latin-1).

        AEMET devuelve a veces ficheros JSON con encoding ``ISO-8859-15``
        o ``latin-1`` (caracteres con tildes), por lo que confiar solo en
        ``apparent_encoding`` puede fallar. Esta función intenta los
        encodings explícitamente y devuelve el texto decodificado.
        """
        raw = response.content
        for enc in ('utf-8', 'iso-8859-15', 'latin-1'):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        # Último recurso: latin-1 nunca falla aunque pueda mojibrear
        return raw.decode('latin-1', errors='replace')

    @classmethod
    def _fetch_datos(cls, datos_url):
        """Descarga el contenido apuntado por la URL ``datos``.

        La URL ``datos`` ya está preautenticada (lleva el token internamente
        en el path firmado por AEMET); por eso aquí **no** añadimos
        ``api_key`` ni headers de autenticación.
        """
        if not datos_url:
            return None
        try:
            response = requests.get(datos_url, timeout=cls.TIMEOUT)
            response.raise_for_status()
            # Decodificación robusta para JSON con encoding ISO-8859-15/latin-1
            text = cls._decode_response(response)
            return json.loads(text)
        except requests.exceptions.RequestException as exc:
            _logger.error("Error descargando datos AEMET %s: %s",
                          datos_url, exc)
            return None
        except ValueError:
            _logger.error("Datos AEMET no JSON: %s", datos_url)
            return None

    @classmethod
    def call(cls, path, api_key, params=None):
        """Patrón completo: pide el endpoint y descarga la URL ``datos``."""
        meta = cls._request(path, api_key, params=params)
        if not meta:
            return None
        return cls._fetch_datos(meta.get('datos'))

    # ---------- Endpoints concretos ----------

    @classmethod
    def get_observaciones_estacion(cls, idema, api_key):
        """Devuelve la lista de observaciones horarias (últimas 12h)."""
        if not idema:
            return None
        path = f"/api/observacion/convencional/datos/estacion/{idema}"
        data = cls.call(path, api_key)
        if not isinstance(data, list):
            return None
        return data

    @classmethod
    def get_inventario_estaciones(cls, api_key):
        """Devuelve el inventario completo de estaciones climatológicas.

        Endpoint según OpenAPI:
            GET /api/valores/climatologicos/inventarioestaciones/todasestaciones

        El campo ``indicativo`` de cada elemento es el IDEMA usado en el
        endpoint de observación convencional. Las estaciones de
        aeropuertos/aeródromos también figuran en este inventario, por lo
        que sirve como tabla de resolución OACI -> IDEMA por nombre.
        """
        # NOTA: el ejemplo del curl oficial añade trailing slash
        # ("/todasestaciones/"). El endpoint funciona con o sin ella; usamos
        # la forma exacta del spec OpenAPI (sin slash final).
        path = "/api/valores/climatologicos/inventarioestaciones/todasestaciones"
        data = cls.call(path, api_key)
        if not isinstance(data, list):
            return None
        return data

    # ---------- Resolución OACI -> IDEMA ----------

    @classmethod
    def resolve_idema(cls, icao_code, api_key, inventario=None):
        """Intenta obtener el indicativo AEMET (idema) para un código OACI.

        Estrategia (en orden):
            1. Mapa estático ``ICAO_TO_IDEMA``.
            2. Inventario AEMET: estación cuyo ``nombre`` contenga el OACI
               completo (en mayúsculas). Algunas estaciones AEMET incluyen
               el código OACI en su nombre.
            3. ``None`` (el llamador deberá usar el buscador de estaciones).
        """
        if not icao_code:
            return None
        icao = icao_code.upper().strip()
        if icao in ICAO_TO_IDEMA:
            return ICAO_TO_IDEMA[icao]

        if inventario is None:
            inventario = cls.get_inventario_estaciones(api_key) or []

        # Coincidencia por OACI literal en el nombre de la estación.
        candidatas = [e for e in inventario
                      if icao in (e.get('nombre') or '').upper()]
        if len(candidatas) == 1:
            return candidatas[0].get('indicativo')
        return None

    # ---------- Normalización de observaciones ----------

    @classmethod
    def parse_observacion(cls, raw):
        """Normaliza un registro de observación AEMET.

        El registro viene con campos en m/s, hPa, °C, km, etc.
        Esta función los convierte a las unidades habituales en METAR
        (kt para viento, m para visibilidad) y devuelve un dict estable.
        """
        if not raw:
            return None

        # Fecha de observación: "fint" en ISO 8601 (puede traer zona)
        fint = raw.get('fint')
        observation_time = None
        if fint:
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S%z'):
                try:
                    dt = datetime.strptime(fint, fmt)
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)  # AEMET ya viene en UTC
                    observation_time = dt
                    break
                except ValueError:
                    continue

        wind_speed_ms = raw.get('vv')
        wind_gust_ms = raw.get('vmax')
        visibility_km = raw.get('vis')

        return {
            'idema': raw.get('idema'),
            'station_name': raw.get('ubi'),
            'latitude': raw.get('lat'),
            'longitude': raw.get('lon'),
            'elevation_m': raw.get('alt'),
            'observation_time': observation_time,
            'temperatura': raw.get('ta'),
            'dewpoint': raw.get('tpr'),
            'humidity': raw.get('hr'),
            'wind_direction': raw.get('dv'),
            'wind_speed_kt': (round(wind_speed_ms * _MS_TO_KT, 1)
                              if wind_speed_ms is not None else None),
            'wind_gust_kt': (round(wind_gust_ms * _MS_TO_KT, 1)
                             if wind_gust_ms is not None else None),
            'wind_speed_ms': wind_speed_ms,
            'wind_gust_ms': wind_gust_ms,
            'visibility_m': (int(visibility_km * 1000)
                             if visibility_km is not None else None),
            'qnh': raw.get('pres_nmar'),
            'pressure': raw.get('pres'),
            'precipitation': raw.get('prec'),
            'snow': raw.get('nieve'),
            'raw': raw,
        }

    @classmethod
    def latest_observation(cls, observaciones):
        """Selecciona la observación más reciente del listado AEMET."""
        if not observaciones:
            return None
        # AEMET devuelve cronológicamente; tomamos la última con fint válido
        valid = [o for o in observaciones if o.get('fint')]
        if not valid:
            return None
        valid.sort(key=lambda o: o.get('fint'))
        return valid[-1]

    # ---------- Sintetizar texto tipo METAR ----------

    @classmethod
    def build_metar_text(cls, parsed, icao_code=None):
        """Genera un string de tipo METAR a partir de la observación.

        Formato (no oficial, derivado de OBS AEMET)::

            <ICAO> DDHHMMZ AUTO dddffGggKT vis TT/DD QNNNN RMK AEMET

        ``vis`` se omite si AEMET no la reporta. El bloque RMK indica
        explícitamente el origen para que el lector no lo confunda con un
        METAR oficial.
        """
        if not parsed:
            return ''

        parts = []
        parts.append((icao_code or parsed.get('idema') or 'XXXX').upper())

        obs_time = parsed.get('observation_time')
        if obs_time:
            parts.append(obs_time.strftime('%d%H%MZ'))

        parts.append('AUTO')

        wind_dir = parsed.get('wind_direction')
        wind_kt = parsed.get('wind_speed_kt')
        gust_kt = parsed.get('wind_gust_kt')
        if wind_dir is not None and wind_kt is not None:
            wind_str = f"{int(wind_dir):03d}{int(round(wind_kt)):02d}"
            if gust_kt and gust_kt - (wind_kt or 0) >= 5:
                wind_str += f"G{int(round(gust_kt)):02d}"
            wind_str += "KT"
            parts.append(wind_str)
        elif wind_kt is not None:
            parts.append(f"VRB{int(round(wind_kt)):02d}KT")

        vis_m = parsed.get('visibility_m')
        if vis_m is not None:
            if vis_m >= 9999:
                parts.append('9999')
            else:
                parts.append(f"{int(vis_m):04d}")

        temp = parsed.get('temperatura')
        dewp = parsed.get('dewpoint')
        if temp is not None and dewp is not None:
            parts.append(f"{cls._fmt_temp(temp)}/{cls._fmt_temp(dewp)}")

        qnh = parsed.get('qnh')
        if qnh is not None:
            parts.append(f"Q{int(round(qnh)):04d}")

        parts.append('RMK AEMET')
        return ' '.join(parts)

    @staticmethod
    def _fmt_temp(t):
        t = int(round(t))
        return f"M{abs(t):02d}" if t < 0 else f"{t:02d}"

    # ---------- API de alto nivel ----------

    @classmethod
    def get_metar_like(cls, api_key, icao_code=None, idema_code=None):
        """Devuelve un dict tipo METAR para el aeródromo solicitado.

        Args:
            api_key: token AEMET
            icao_code: código OACI (opcional si idema_code informado)
            idema_code: indicativo AEMET (opcional si icao_code informado)

        Returns:
            dict con los datos parseados + ``raw_metar`` sintético, o ``None``
            si no se ha podido resolver.
        """
        idema = (idema_code or '').strip() or None
        if not idema and icao_code:
            idema = cls.resolve_idema(icao_code, api_key)
        if not idema:
            _logger.warning(
                "AEMET: no se pudo resolver IDEMA para OACI=%s", icao_code)
            return None

        observaciones = cls.get_observaciones_estacion(idema, api_key)
        last = cls.latest_observation(observaciones)
        if not last:
            _logger.warning(
                "AEMET: sin observaciones recientes para IDEMA=%s", idema)
            return None

        parsed = cls.parse_observacion(last)
        if not parsed:
            return None

        parsed['icao'] = (icao_code or '').upper() or None
        parsed['idema'] = idema
        parsed['raw_metar'] = cls.build_metar_text(parsed, icao_code=icao_code)
        return parsed

    # ---------- Validación de la API key ----------

    @classmethod
    def validate_api_key(cls, api_key):
        """Hace una llamada ligera para comprobar si la key funciona."""
        if not api_key:
            return False
        # Endpoint pequeño y cacheado
        meta = cls._request("/api/maestro/municipios", api_key)
        return meta is not None
