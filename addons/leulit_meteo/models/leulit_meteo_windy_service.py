# -*- coding: utf-8 -*-

import logging
import requests
from datetime import datetime
from odoo.exceptions import UserError
from odoo import _

_logger = logging.getLogger(__name__)


class WindyService:
    """
    Servicio para integración con Windy API
    https://api.windy.com/
    
    Requiere API Key que se puede obtener en:
    https://api.windy.com/keys
    """
    
    BASE_URL = "https://api.windy.com/api"
    
    @staticmethod
    def get_point_forecast(lat, lon, api_key, model='gfs'):
        """
        Obtiene pronóstico puntual de Windy
        
        Args:
            lat (float): Latitud
            lon (float): Longitud
            api_key (str): API Key de Windy
            model (str): Modelo meteorológico (gfs, ecmwf, etc.)
        
        Returns:
            dict: Datos meteorológicos del punto
        """
        if not api_key:
            raise UserError(_('Se requiere una API Key de Windy. Configure en Ajustes > Meteorología'))
        
        endpoint = f"{WindyService.BASE_URL}/point-forecast/v2"
        
        payload = {
            "lat": lat,
            "lon": lon,
            "model": model,
            "parameters": ["wind", "temp", "dewpoint", "rh", "pressure", "cloudcover", "precip"],
            "levels": ["surface"],
            "key": api_key
        }
        
        try:
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                return WindyService._parse_point_forecast(data)
            else:
                error_msg = data.get('message', 'Error desconocido')
                raise UserError(_('Error en Windy API: %s') % error_msg)
                
        except requests.RequestException as e:
            _logger.error("Error al consultar Windy API: %s", str(e))
            raise UserError(_('Error al conectar con Windy: %s') % str(e))
    
    @staticmethod
    def _parse_point_forecast(data):
        """
        Procesa la respuesta de Windy y extrae los datos relevantes
        
        Args:
            data (dict): Respuesta JSON de la API
        
        Returns:
            dict: Datos procesados
        """
        try:
            # Windy devuelve arrays paralelos de timestamps y valores
            # Tomamos el primer valor (más reciente/actual)
            ts = data.get('ts', [])
            
            result = {
                'timestamp': ts[0] if ts else None,
                'modelo': data.get('model', 'N/A'),
                'temperatura': None,
                'punto_rocio': None,
                'humedad': None,
                'presion': None,
                'cobertura_nubes': None,
                'precipitacion': None,
                'viento_velocidad': None,
                'viento_direccion': None,
                'viento_rachas': None,
            }
            
            # Temperatura (convertir de Kelvin a Celsius si es necesario)
            if 'temp-surface' in data:
                temp_values = data['temp-surface']
                if temp_values:
                    temp = temp_values[0]
                    # Windy suele devolver en Kelvin, convertir a Celsius
                    result['temperatura'] = temp - 273.15 if temp > 200 else temp
            
            # Punto de rocío
            if 'dewpoint-surface' in data:
                dewpoint_values = data['dewpoint-surface']
                if dewpoint_values:
                    dp = dewpoint_values[0]
                    result['punto_rocio'] = dp - 273.15 if dp > 200 else dp
            
            # Humedad relativa
            if 'rh-surface' in data:
                rh_values = data['rh-surface']
                if rh_values:
                    result['humedad'] = rh_values[0]
            
            # Presión (superficie)
            if 'pressure-surface' in data:
                pressure_values = data['pressure-surface']
                if pressure_values:
                    result['presion'] = pressure_values[0]
            
            # Cobertura de nubes
            if 'cloudcover-surface' in data:
                cloud_values = data['cloudcover-surface']
                if cloud_values:
                    result['cobertura_nubes'] = cloud_values[0]
            
            # Precipitación
            if 'precip-surface' in data:
                precip_values = data['precip-surface']
                if precip_values:
                    result['precipitacion'] = precip_values[0]
            
            # Viento (componentes U y V o directo)
            if 'wind_u-surface' in data and 'wind_v-surface' in data:
                u_values = data['wind_u-surface']
                v_values = data['wind_v-surface']
                if u_values and v_values:
                    u = u_values[0]
                    v = v_values[0]
                    # Calcular velocidad y dirección del viento
                    import math
                    speed = math.sqrt(u**2 + v**2)
                    direction = (math.degrees(math.atan2(u, v)) + 180) % 360
                    result['viento_velocidad'] = speed * 3.6  # m/s a km/h
                    result['viento_direccion'] = direction
            
            # Rachas de viento
            if 'gust-surface' in data:
                gust_values = data['gust-surface']
                if gust_values:
                    result['viento_rachas'] = gust_values[0] * 3.6  # m/s a km/h
            
            return result
            
        except Exception as e:
            _logger.error("Error al procesar respuesta de Windy: %s", str(e))
            raise UserError(_('Error al procesar datos de Windy: %s') % str(e))
    
    @staticmethod
    def get_polyline_forecast(points, api_key, model='gfs'):
        """
        Obtiene pronóstico para una polilínea (múltiples puntos)
        
        Args:
            points (list): Lista de tuplas [(lat, lon), ...]
            api_key (str): API Key de Windy
            model (str): Modelo meteorológico
        
        Returns:
            list: Lista de diccionarios con datos por punto
        """
        results = []
        for i, (lat, lon) in enumerate(points):
            try:
                _logger.info(f"Consultando punto {i+1}/{len(points)}: ({lat}, {lon})")
                forecast = WindyService.get_point_forecast(lat, lon, api_key, model)
                forecast['punto_indice'] = i
                forecast['latitud'] = lat
                forecast['longitud'] = lon
                results.append(forecast)
            except Exception as e:
                _logger.warning(f"Error al consultar punto {i}: {str(e)}")
                # Agregar punto con error
                results.append({
                    'punto_indice': i,
                    'latitud': lat,
                    'longitud': lon,
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def validate_api_key(api_key):
        """
        Valida que la API Key sea válida haciendo una consulta simple
        
        Args:
            api_key (str): API Key a validar
        
        Returns:
            bool: True si la key es válida
        """
        try:
            # Consulta simple para validar (Madrid)
            WindyService.get_point_forecast(40.4168, -3.7038, api_key)
            return True
        except UserError:
            return False
