# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime

_logger = logging.getLogger(__name__)


class OpenMeteoService:
    """Servicio para conectar con la API de Open-Meteo"""
    
    BASE_URL = "https://api.open-meteo.com/v1"
    
    @staticmethod
    def get_current_weather(latitude, longitude):
        """
        Obtiene el clima actual para una ubicación específica
        
        Args:
            latitude (float): Latitud de la ubicación
            longitude (float): Longitud de la ubicación
            
        Returns:
            dict: Datos meteorológicos o None si hay error
        """
        try:
            url = f"{OpenMeteoService.BASE_URL}/forecast"
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,'
                          'precipitation,rain,weather_code,cloud_cover,wind_speed_10m,'
                          'wind_direction_10m,wind_gusts_10m',
                'timezone': 'auto'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            _logger.info(f"Datos meteorológicos obtenidos para lat={latitude}, lon={longitude}")
            return data
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al consultar Open-Meteo API: {str(e)}")
            return None
    
    @staticmethod
    def get_forecast(latitude, longitude, days=7):
        """
        Obtiene el pronóstico meteorológico para varios días
        
        Args:
            latitude (float): Latitud de la ubicación
            longitude (float): Longitud de la ubicación
            days (int): Número de días de pronóstico (1-16)
            
        Returns:
            dict: Datos de pronóstico o None si hay error
        """
        try:
            url = f"{OpenMeteoService.BASE_URL}/forecast"
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'daily': 'weather_code,temperature_2m_max,temperature_2m_min,'
                        'precipitation_sum,rain_sum,wind_speed_10m_max,wind_gusts_10m_max,'
                        'wind_direction_10m_dominant',
                'timezone': 'auto',
                'forecast_days': min(days, 16)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            _logger.info(f"Pronóstico obtenido para lat={latitude}, lon={longitude}, días={days}")
            return data
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al consultar pronóstico Open-Meteo: {str(e)}")
            return None
    
    @staticmethod
    def get_weather_description(weather_code):
        """
        Convierte el código de clima WMO en descripción legible
        
        Args:
            weather_code (int): Código WMO del clima
            
        Returns:
            str: Descripción del clima en español
        """
        weather_codes = {
            0: 'Despejado',
            1: 'Principalmente despejado',
            2: 'Parcialmente nublado',
            3: 'Nublado',
            45: 'Niebla',
            48: 'Niebla con escarcha',
            51: 'Llovizna ligera',
            53: 'Llovizna moderada',
            55: 'Llovizna densa',
            56: 'Llovizna helada ligera',
            57: 'Llovizna helada densa',
            61: 'Lluvia ligera',
            63: 'Lluvia moderada',
            65: 'Lluvia intensa',
            66: 'Lluvia helada ligera',
            67: 'Lluvia helada intensa',
            71: 'Nevada ligera',
            73: 'Nevada moderada',
            75: 'Nevada intensa',
            77: 'Granizo',
            80: 'Chubascos ligeros',
            81: 'Chubascos moderados',
            82: 'Chubascos violentos',
            85: 'Chubascos de nieve ligeros',
            86: 'Chubascos de nieve intensos',
            95: 'Tormenta',
            96: 'Tormenta con granizo ligero',
            99: 'Tormenta con granizo intenso',
        }
        return weather_codes.get(weather_code, 'Desconocido')
