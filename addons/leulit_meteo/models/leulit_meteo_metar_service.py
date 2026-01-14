# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime
import re

_logger = logging.getLogger(__name__)


class AviationWeatherService:
    """Servicio para conectar con la API de Aviation Weather (aviationweather.gov)"""
    
    BASE_URL = "https://aviationweather.gov/api/data"
    
    @staticmethod
    def get_metar(icao_code, hours_before=2):
        """
        Obtiene el METAR más reciente para un aeródromo
        
        Args:
            icao_code (str): Código OACI del aeródromo (ej: LECU, LEBL)
            hours_before (int): Horas anteriores para buscar (default: 2)
            
        Returns:
            dict: Datos METAR parseados o None si hay error
        """
        try:
            url = f"{AviationWeatherService.BASE_URL}/metar"
            params = {
                'ids': icao_code.upper(),
                'format': 'json',
                'hours': hours_before,
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                # Tomar el METAR más reciente
                metar = data[0]
                _logger.info(f"METAR obtenido para {icao_code}: {metar.get('rawOb', '')}")
                return AviationWeatherService._parse_metar(metar)
            else:
                _logger.warning(f"No se encontró METAR para {icao_code}")
                return None
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al consultar Aviation Weather API: {str(e)}")
            return None
    
    @staticmethod
    def get_taf(icao_code):
        """
        Obtiene el TAF (Terminal Aerodrome Forecast) para un aeródromo
        
        Args:
            icao_code (str): Código OACI del aeródromo
            
        Returns:
            dict: Datos TAF o None si hay error
        """
        try:
            url = f"{AviationWeatherService.BASE_URL}/taf"
            params = {
                'ids': icao_code.upper(),
                'format': 'json',
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data and len(data) > 0:
                taf = data[0]
                _logger.info(f"TAF obtenido para {icao_code}")
                return AviationWeatherService._parse_taf(taf)
            else:
                _logger.warning(f"No se encontró TAF para {icao_code}")
                return None
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al consultar TAF: {str(e)}")
            return None
    
    @staticmethod
    def _parse_metar(metar_data):
        """
        Parsea los datos METAR del JSON de la API
        
        Args:
            metar_data (dict): Datos JSON del METAR
            
        Returns:
            dict: Datos parseados
        """
        return {
            'raw': metar_data.get('rawOb', ''),
            'icao': metar_data.get('icaoId', ''),
            'observation_time': metar_data.get('obsTime'),
            'report_time': metar_data.get('reportTime'),
            'temperature': metar_data.get('temp'),
            'dewpoint': metar_data.get('dewp'),
            'wind_dir': metar_data.get('wdir'),
            'wind_speed': metar_data.get('wspd'),
            'wind_gust': metar_data.get('wgst'),
            'visibility': metar_data.get('visib'),
            'altimeter': metar_data.get('altim'),
            'qnh': metar_data.get('slp'),  # Sea Level Pressure
            'flight_category': metar_data.get('fltcat'),  # VFR, MVFR, IFR, LIFR
            'clouds': metar_data.get('clouds', []),
            'weather': metar_data.get('wxString', ''),
            'latitude': metar_data.get('lat'),
            'longitude': metar_data.get('lon'),
            'elevation': metar_data.get('elev'),
        }
    
    @staticmethod
    def _parse_taf(taf_data):
        """
        Parsea los datos TAF del JSON de la API
        
        Args:
            taf_data (dict): Datos JSON del TAF
            
        Returns:
            dict: Datos parseados
        """
        return {
            'raw': taf_data.get('rawTAF', ''),
            'icao': taf_data.get('icaoId', ''),
            'issue_time': taf_data.get('issueTime'),
            'bulletin_time': taf_data.get('bulletinTime'),
            'valid_time_from': taf_data.get('validTimeFrom'),
            'valid_time_to': taf_data.get('validTimeTo'),
            'latitude': taf_data.get('lat'),
            'longitude': taf_data.get('lon'),
            'elevation': taf_data.get('elev'),
        }
    
    @staticmethod
    def get_flight_category_description(category):
        """
        Obtiene descripción de la categoría de vuelo
        
        Args:
            category (str): Código de categoría (VFR, MVFR, IFR, LIFR)
            
        Returns:
            str: Descripción en español
        """
        categories = {
            'VFR': 'VFR - Reglas de Vuelo Visual (>5000ft, >5mi)',
            'MVFR': 'MVFR - VFR Marginal (3000-5000ft, 3-5mi)',
            'IFR': 'IFR - Reglas de Vuelo por Instrumentos (1000-3000ft, 1-3mi)',
            'LIFR': 'LIFR - IFR Bajo (<1000ft, <1mi)',
        }
        return categories.get(category, category or 'Desconocido')
    
    @staticmethod
    def parse_metar_raw(raw_metar):
        """
        Parsea un METAR en formato texto a componentes básicos
        
        Args:
            raw_metar (str): METAR en formato texto
            
        Returns:
            dict: Componentes parseados
        """
        if not raw_metar:
            return {}
        
        result = {'raw': raw_metar}
        
        # Extraer código OACI (4 letras al inicio)
        icao_match = re.search(r'\b([A-Z]{4})\b', raw_metar)
        if icao_match:
            result['icao'] = icao_match.group(1)
        
        # Extraer fecha/hora (formato DDHHMMZ)
        time_match = re.search(r'(\d{6}Z)', raw_metar)
        if time_match:
            result['time'] = time_match.group(1)
        
        # Extraer viento (formato DDDSSKT o DDDSSGSSGKT)
        wind_match = re.search(r'(\d{3}|VRB)(\d{2,3})(G(\d{2,3}))?(KT|MPS)', raw_metar)
        if wind_match:
            result['wind_dir'] = wind_match.group(1)
            result['wind_speed'] = wind_match.group(2)
            if wind_match.group(4):
                result['wind_gust'] = wind_match.group(4)
        
        # Extraer visibilidad
        vis_match = re.search(r'(\d{4})\s', raw_metar)
        if vis_match:
            result['visibility'] = vis_match.group(1)
        
        # Extraer temperatura/punto de rocío (TT/DD)
        temp_match = re.search(r'(M?\d{2})/(M?\d{2})', raw_metar)
        if temp_match:
            temp_str = temp_match.group(1)
            dewp_str = temp_match.group(2)
            result['temp'] = int(temp_str.replace('M', '-'))
            result['dewpoint'] = int(dewp_str.replace('M', '-'))
        
        # Extraer QNH (formato QXXXX o AXXXX)
        qnh_match = re.search(r'Q(\d{4})|A(\d{4})', raw_metar)
        if qnh_match:
            if qnh_match.group(1):
                result['qnh'] = int(qnh_match.group(1))  # En hPa
            elif qnh_match.group(2):
                result['altimeter'] = float(qnh_match.group(2)) / 100  # En inHg
        
        return result
