# -*- coding: utf-8 -*-
"""
Leulit Meteorología - Documentación del Módulo
===============================================

Integración con Open-Meteo API para consultas meteorológicas en tiempo real.

Autor: Leulit
Versión: 17.0.1.0.0
Licencia: LGPL-3

Descripción General
-------------------
Este módulo proporciona integración con la API de Open-Meteo (https://open-meteo.com/)
para obtener información meteorológica actual y pronósticos para ubicaciones específicas.

Características Principales
----------------------------
1. Consulta de clima actual (temperatura, humedad, precipitación, viento)
2. Obtención de pronósticos meteorológicos (hasta 16 días)
3. Almacenamiento de histórico de consultas
4. Integración con otros módulos (vuelos, operaciones)
5. Traducción automática de códigos meteorológicos WMO

Modelos
-------
leulit.meteo.consulta
    Modelo principal que almacena las consultas meteorológicas.
    
    Campos principales:
    - codigo: Código secuencial único (METEO-XXXXX)
    - ubicacion: Nombre descriptivo de la ubicación
    - latitud/longitud: Coordenadas GPS
    - fecha_consulta: Timestamp de la consulta
    - tipo_consulta: 'actual' o 'pronostico'
    - temperatura, humedad, precipitacion: Datos meteorológicos
    - velocidad_viento, direccion_viento, rachas_viento: Datos de viento
    - codigo_clima: Código WMO de condiciones
    - descripcion_clima: Descripción en español (computed)
    
    Métodos principales:
    - action_consultar_clima_actual(): Consulta clima actual desde API
    - action_consultar_pronostico(): Obtiene pronóstico meteorológico
    - consultar_clima_ubicacion(): Helper para consultas programáticas

Servicios
---------
OpenMeteoService
    Clase de servicio estática para conectar con Open-Meteo API.
    
    Métodos:
    - get_current_weather(lat, lon): Obtiene clima actual
    - get_forecast(lat, lon, days): Obtiene pronóstico
    - get_weather_description(code): Traduce código WMO

Vistas
------
- view_leulit_meteo_consulta_tree: Vista de lista
- view_leulit_meteo_consulta_form: Vista de formulario con botones de acción
- view_leulit_meteo_consulta_search: Vista de búsqueda con filtros

Menús
-----
Meteorología (menu_leulit_meteo_root)
└── Consultas (menu_leulit_meteo_consultas)

Seguridad
---------
Grupos con acceso:
- leulit.RBase: Lectura, escritura, creación (sin eliminación)
- leulit.RBase_employee: Acceso completo (CRUD)

Dependencias
------------
Módulos Odoo:
- leulit (módulo base)
- mail (chatter y tracking)

Python:
- requests (>=2.25.0)

API Externa:
- Open-Meteo API (https://api.open-meteo.com/v1)
  * Sin autenticación requerida
  * Sin límites de rate
  * Gratuito para uso no comercial y comercial

Instalación
-----------
1. Instalar dependencia Python:
   $ pip install requests
   
2. Instalar módulo desde Odoo:
   Aplicaciones → Actualizar lista → Buscar "Leulit Meteorología" → Instalar

3. Verificar: Debe aparecer menú "Meteorología" en navegación principal

Configuración
-------------
No requiere configuración adicional. El módulo funciona inmediatamente después
de la instalación.

Uso Básico
----------
1. Ir a Meteorología → Consultas
2. Crear nuevo registro
3. Introducir ubicación, latitud y longitud
4. Hacer clic en "Consultar Clima Actual" o "Obtener Pronóstico"
5. Los datos se actualizan automáticamente

Integración con Otros Módulos
------------------------------
Ejemplo 1: Consultar clima desde otro módulo
```python
meteo_obj = self.env['leulit.meteo.consulta']
datos = meteo_obj.consultar_clima_ubicacion(
    ubicacion='Madrid LECU',
    latitud=40.3717,
    longitud=-3.7856
)
if datos:
    temperatura = datos['temperatura']
    viento = datos['viento']
```

Ejemplo 2: Heredar modelo de vuelo para añadir campo meteorológico
```python
class LeulitVuelo(models.Model):
    _inherit = 'leulit.vuelo'
    
    meteo_consulta_id = fields.Many2one(
        'leulit.meteo.consulta',
        string='Datos Meteorológicos'
    )
    
    def action_obtener_meteo(self):
        consulta = self.env['leulit.meteo.consulta'].create({
            'ubicacion': self.aerodromo_salida_id.name,
            'latitud': self.aerodromo_salida_id.latitud,
            'longitud': self.aerodromo_salida_id.longitud,
            'vuelo_id': self.id,
        })
        consulta.action_consultar_clima_actual()
        self.meteo_consulta_id = consulta.id
```

Ejemplo 3: Consultar directamente la API
```python
from odoo.addons.leulit_meteo.models.leulit_meteo_service import OpenMeteoService

data = OpenMeteoService.get_current_weather(40.3717, -3.7856)
if data and 'current' in data:
    temperatura = data['current']['temperature_2m']
    viento = data['current']['wind_speed_10m']
```

Ubicaciones de Ejemplo (Aeródromos Españoles)
----------------------------------------------
Madrid - Cuatro Vientos (LECU): lat=40.3717, lon=-3.7856
Sabadell (LELL): lat=41.5209, lon=2.1050
Granada - Armilla (LEGA): lat=37.1331, lon=-3.6356
Valencia (LEVC): lat=39.4893, lon=-0.4816
Sevilla (LEZL): lat=37.4180, lon=-5.8931
Barcelona - El Prat (LEBL): lat=41.2974, lon=2.0833
Málaga (LEMG): lat=36.6749, lon=-4.4991

Códigos Meteorológicos WMO
---------------------------
0: Despejado
1-3: Despejado/Parcialmente nublado/Nublado
45-48: Niebla
51-57: Llovizna (ligera/moderada/densa)
61-67: Lluvia (ligera/moderada/intensa)
71-77: Nevada
80-82: Chubascos
85-86: Chubascos de nieve
95-99: Tormenta (con/sin granizo)

Solución de Problemas
----------------------
Error: "No se pudo obtener información meteorológica"
- Verificar conexión a internet
- Comprobar coordenadas válidas (-90 a 90 lat, -180 a 180 lon)
- Revisar logs de Odoo

Error: "ModuleNotFoundError: No module named 'requests'"
- Ejecutar: pip install requests
- Reiniciar servidor Odoo

Timeout en consultas:
- Verificar velocidad de conexión
- Aumentar timeout en leulit_meteo_service.py (default: 10s)
- Implementar sistema de caché

Mejoras Futuras
---------------
- Sistema de caché para reducir llamadas a API
- Widgets visuales (gráficos, rosa de vientos)
- Consultas automáticas programadas
- Alertas meteorológicas por email
- Integración con METAR/TAF
- Vista móvil optimizada
- Mapa interactivo de ubicaciones
- Análisis de histórico y tendencias

Notas de Desarrollo
-------------------
- La API de Open-Meteo no requiere autenticación
- Los datos se almacenan en la base de datos de Odoo
- Las consultas tienen timeout de 10 segundos
- Los errores se registran en el log de Odoo
- El modelo hereda de mail.thread para trazabilidad

Referencias
-----------
- Open-Meteo API: https://open-meteo.com/en/docs
- Documentación WMO: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
- Proyecto Helipistas ERP: Sistema de gestión aeronáutica basado en Odoo 17

Licencia
--------
LGPL-3 - GNU Lesser General Public License v3.0

Autor
-----
Leulit (https://www.leulit.com)

Historial de Versiones
-----------------------
17.0.1.0.0 (2026-01-13)
    - Versión inicial
    - Integración con Open-Meteo API
    - Consultas de clima actual y pronósticos
    - Vistas completas (tree, form, search)
    - Seguridad configurada
    - Documentación completa
"""

__version__ = '17.0.1.0.0'
__author__ = 'Leulit'
__license__ = 'LGPL-3'
