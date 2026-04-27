# -*- coding: utf-8 -*-
"""Cliente AEMET OpenData para mensajes oficiales METAR/TAF/SIGMET.

Este servicio se centra en obtener los **mensajes oficiales** que AEMET
publica en su OpenData para aviación:

    * METAR  -> ``/api/observacion/convencional/mensajes/tipomensaje/METAR/id/{icao}``
    * TAF    -> ``/api/observacion/convencional/mensajes/tipomensaje/TAF/id/{icao}``
    * SIGMET -> ``/api/observacion/convencional/mensajes/tipomensaje/SIGMET/id/{fir}``

NOTA: la spec OpenAPI publicada por AEMET
(``/observacion/convencional/mensajes/tipomensaje/{tipomensaje}``) sólo
documenta los tipos SYNOP/TEMP/CLIMAT. Las variantes con sufijo
``/id/{icao}`` o ``/id/{fir}`` para METAR/TAF/SIGMET **no figuran en la
spec** pero están operativas (se usan con curl en producción contra
AEMET). Las invocamos directamente; si AEMET las retira, este servicio
devolverá ``None`` y el flujo de UI lo tratará como "sin datos".

Patrón de 2 llamadas habitual de AEMET:
    1. Llamada al endpoint con ``?api_key=<JWT>`` -> JSON con campo ``datos``
       (URL temporal preautenticada).
    2. Descarga del contenido apuntado por ``datos`` (texto plano para
       METAR/TAF/SIGMET).

El RAW del METAR/TAF/SIGMET **NO se altera**: legalmente importante para
AESA. El parseo derivado (temperatura, viento, ...) se hace en el módulo
``leulit_meteo_metar_parser`` y nunca modifica el texto original.
"""

import json
import logging
import requests

_logger = logging.getLogger(__name__)


class AemetOpenDataService:
    """Cliente para la API AEMET OpenData (mensajes oficiales)."""

    BASE_URL = "https://opendata.aemet.es/opendata"
    TIMEOUT = 20

    # ---------- Helpers internos ----------

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
                "AEMET %s -> 404 Not Found: recurso no encontrado (%s)",
                path, descripcion)
        elif estado_int == 429:
            _logger.warning(
                "AEMET %s -> 429 Too Many Requests: límite de peticiones "
                "excedido. Reintenta más tarde (%s)", path, descripcion)
        else:
            _logger.error(
                "AEMET %s -> estado %s: %s", path, estado, descripcion)

    @classmethod
    def _request_meta(cls, path, api_key, params=None):
        """Primera llamada AEMET; devuelve dict con campo ``datos`` (URL).

        Auth ``?api_key=<JWT>`` como query param (patrón documentado por
        el Centro de Descargas de AEMET, ver ejemplo de curl en la web).
        """
        if not api_key:
            _logger.error("AEMET API key no configurada")
            return None

        url = f"{cls.BASE_URL}{path}"
        headers = {
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
        }
        query = dict(params or {})
        query['api_key'] = api_key
        try:
            response = requests.get(
                url, headers=headers, params=query, timeout=cls.TIMEOUT)
            status = response.status_code
            if status in (401, 404, 429):
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
            estado = payload.get('estado') if isinstance(
                payload, dict) else None
            if estado in (200, None):
                return payload
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
        """Decodifica una respuesta probando utf-8 -> iso-8859-15 -> latin-1.

        AEMET sirve a veces ficheros con ISO-8859-15 (caracteres con
        tildes), por lo que confiar solo en ``apparent_encoding`` falla.
        """
        raw = response.content
        for enc in ('utf-8', 'iso-8859-15', 'latin-1'):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode('latin-1', errors='replace')

    @classmethod
    def _fetch_text(cls, datos_url):
        """Descarga texto plano (METAR/TAF/SIGMET) desde la URL ``datos``.

        La URL ``datos`` ya está preautenticada por AEMET (token firmado
        en el path), por lo que aquí no añadimos ``api_key`` ni headers.
        """
        if not datos_url:
            return None
        try:
            response = requests.get(datos_url, timeout=cls.TIMEOUT)
            response.raise_for_status()
            text = cls._decode_response(response)
            # Algunos endpoints devuelven un JSON con un único string
            # cuando se piden a través de RSS; la inmensa mayoría devuelve
            # texto plano. Devolvemos el texto tal cual; el parser ya
            # trabaja con ello.
            return text.strip() or None
        except requests.exceptions.RequestException as exc:
            _logger.error("Error descargando datos AEMET %s: %s",
                          datos_url, exc)
            return None

    @classmethod
    def _fetch_json(cls, datos_url):
        """Descarga el contenido apuntado por ``datos`` y lo parsea como JSON.

        Útil para endpoints que devuelven listas/dicts (validate_api_key).
        """
        if not datos_url:
            return None
        try:
            response = requests.get(datos_url, timeout=cls.TIMEOUT)
            response.raise_for_status()
            text = cls._decode_response(response)
            return json.loads(text)
        except requests.exceptions.RequestException as exc:
            _logger.error("Error descargando datos AEMET %s: %s",
                          datos_url, exc)
            return None
        except ValueError:
            _logger.error("Datos AEMET no JSON: %s", datos_url)
            return None

    # ---------- API pública ----------

    @classmethod
    def get_message(cls, tipomensaje, identifier, api_key):
        """Devuelve el texto crudo de un mensaje oficial METAR/TAF/SIGMET.

        Args:
            tipomensaje: 'METAR' | 'TAF' | 'SIGMET'.
            identifier: código OACI (METAR/TAF) o FIR (SIGMET).
            api_key: token JWT de AEMET.

        Returns:
            str con el texto crudo del mensaje, o ``None``.

        El RAW devuelto se entrega al modelo Odoo SIN modificación.
        """
        if not tipomensaje or not identifier or not api_key:
            return None
        tm = tipomensaje.upper().strip()
        ident = identifier.upper().strip()
        path = (
            f"/api/observacion/convencional/mensajes/"
            f"tipomensaje/{tm}/id/{ident}"
        )
        meta = cls._request_meta(path, api_key)
        if not meta:
            return None
        return cls._fetch_text(meta.get('datos'))

    @classmethod
    def validate_api_key(cls, api_key):
        """Llamada ligera para verificar que la key funciona.

        Usa ``/api/maestro/municipios``, un endpoint público y cacheado.
        """
        if not api_key:
            return False
        meta = cls._request_meta("/api/maestro/municipios", api_key)
        return meta is not None

    # ---------- Inventario de estaciones ----------

    @classmethod
    def get_inventario_estaciones(cls, api_key):
        """Devuelve la lista completa de estaciones climatológicas AEMET."""
        path = "/api/valores/climatologicos/inventarioestaciones/todasestaciones"
        meta = cls._request_meta(path, api_key)
        if not meta:
            return None
        datos_url = meta.get('datos')
        if not datos_url:
            return None
        try:
            r = requests.get(datos_url, timeout=cls.TIMEOUT)
            r.raise_for_status()
            text = cls._decode_response(r)
            import json as _json
            data = _json.loads(text)
            return data if isinstance(data, list) else None
        except Exception as exc:
            _logger.error("AEMET inventario estaciones: %s", exc)
            return None

    @classmethod
    def get_observaciones_estacion(cls, idema, api_key):
        """Devuelve la lista de observaciones horarias (últimas 24h)."""
        if not idema:
            return None
        path = f"/api/observacion/convencional/datos/estacion/{idema}"
        meta = cls._request_meta(path, api_key)
        if not meta:
            return None
        datos_url = meta.get('datos')
        if not datos_url:
            return None
        try:
            r = requests.get(datos_url, timeout=cls.TIMEOUT)
            r.raise_for_status()
            text = cls._decode_response(r)
            import json as _json
            data = _json.loads(text)
            return data if isinstance(data, list) else None
        except Exception as exc:
            _logger.error("AEMET observacion %s: %s", idema, exc)
            return None

    @classmethod
    def _dms_to_decimal(cls, dms_str):
        """Convierte formato DMS de AEMET ('411450N', '0020630E') a decimal."""
        if not dms_str:
            return None
        s = str(dms_str).strip().upper()
        direction = s[-1]
        dms = s[:-1]
        try:
            if direction in ('N', 'S'):
                deg = int(dms[:2]); mn = int(dms[2:4]); sec = int(dms[4:6]) if len(dms) >= 6 else 0
            else:
                deg = int(dms[:3]); mn = int(dms[3:5]); sec = int(dms[5:7]) if len(dms) >= 7 else 0
            val = deg + mn / 60.0 + sec / 3600.0
            if direction in ('S', 'W'):
                val = -val
            return val
        except (ValueError, IndexError):
            try:
                val = float(dms)
                return -val if direction in ('S', 'W') else val
            except ValueError:
                return None

    @classmethod
    def parse_station_coords(cls, station_entry):
        """Extrae (lat, lon) decimal de un entry del inventario AEMET."""
        lat_raw = station_entry.get('latitud')
        lon_raw = station_entry.get('longitud')
        lat = cls._dms_to_decimal(lat_raw)
        lon = cls._dms_to_decimal(lon_raw)
        return lat, lon

    @classmethod
    def find_nearest_station(cls, lat, lon, inventario):
        """Devuelve el entry del inventario AEMET más próximo a (lat, lon)."""
        import math
        best = None
        best_dist = float('inf')
        for entry in inventario:
            slat, slon = cls.parse_station_coords(entry)
            if slat is None or slon is None:
                continue
            φ1, φ2 = math.radians(lat), math.radians(slat)
            dφ = math.radians(slat - lat)
            dλ = math.radians(slon - lon)
            a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
            dist = 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            if dist < best_dist:
                best_dist = dist
                best = entry
        if best is None:
            return None, None
        return best, round(best_dist, 1)

    @classmethod
    def latest_observation(cls, observaciones):
        """Selecciona la observación más reciente del listado AEMET."""
        if not observaciones:
            return None
        valid = [o for o in observaciones if o.get('fint')]
        if not valid:
            return None
        valid.sort(key=lambda o: o['fint'])
        return valid[-1]

    @classmethod
    def parse_observacion(cls, raw):
        """Normaliza un registro de observación AEMET a unidades METAR."""
        if not raw:
            return None
        from datetime import datetime
        fint = raw.get('fint')
        observation_time = None
        if fint:
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S%z'):
                try:
                    dt = datetime.strptime(fint, fmt)
                    observation_time = dt.replace(tzinfo=None)
                    break
                except ValueError:
                    continue
        wind_ms = raw.get('vv')
        gust_ms = raw.get('vmax')
        vis_km = raw.get('vis')
        _MS_TO_KT = 1.943844
        return {
            'idema': raw.get('idema'),
            'station_name': raw.get('ubi'),
            'observation_time': observation_time,
            'temperatura': raw.get('ta'),
            'dewpoint': raw.get('tpr'),
            'humidity': raw.get('hr'),
            'wind_direction': raw.get('dv'),
            'wind_speed_kt': round(wind_ms * _MS_TO_KT, 1) if wind_ms is not None else None,
            'wind_gust_kt': round(gust_ms * _MS_TO_KT, 1) if gust_ms is not None else None,
            'visibility_m': int(vis_km * 1000) if vis_km is not None else None,
            'qnh': raw.get('pres_nmar'),
            'pressure': raw.get('pres'),
        }

    @classmethod
    def build_metar_synthetic(cls, parsed, icao_code=None):
        """Genera texto METAR sintético a partir de observación AEMET (no oficial)."""
        if not parsed:
            return ''
        parts = [(icao_code or parsed.get('idema') or 'XXXX').upper()]
        ot = parsed.get('observation_time')
        if ot:
            parts.append(ot.strftime('%d%H%MZ'))
        parts.append('AUTO')
        wd = parsed.get('wind_direction')
        ws = parsed.get('wind_speed_kt')
        wg = parsed.get('wind_gust_kt')
        if ws is not None:
            if wd is not None:
                ws_str = f"{int(wd):03d}{int(round(ws)):02d}"
            else:
                ws_str = f"VRB{int(round(ws)):02d}"
            if wg and wg - ws >= 5:
                ws_str += f"G{int(round(wg)):02d}"
            parts.append(ws_str + "KT")
        vis = parsed.get('visibility_m')
        if vis is not None:
            parts.append('9999' if vis >= 9999 else f"{int(vis):04d}")
        def fmt_t(t):
            t = int(round(t))
            return f"M{abs(t):02d}" if t < 0 else f"{t:02d}"
        temp = parsed.get('temperatura')
        dewp = parsed.get('dewpoint')
        if temp is not None and dewp is not None:
            parts.append(f"{fmt_t(temp)}/{fmt_t(dewp)}")
        qnh = parsed.get('qnh')
        if qnh is not None:
            parts.append(f"Q{int(round(qnh)):04d}")
        parts.append('RMK AEMET-OBS')
        return ' '.join(parts)
