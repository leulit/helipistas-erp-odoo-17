# -*- coding: utf-8 -*-

from . import leulit_meteo_consulta
from . import leulit_meteo_consulta_punto
from . import leulit_meteo_service
from . import leulit_meteo_windy_service
from . import leulit_meteo_aemet_service
from . import leulit_meteo_openaip_service
from . import leulit_meteo_checkwx_service
from . import leulit_meteo_aviation_weather_service

# Aeródromos de referencia (necesario antes del proveedor AEMET, que
# llama a env['leulit.meteo.icao.reference'].resolve()).
from . import leulit_meteo_icao_reference

# Parser ligero del METAR (best-effort).
from . import leulit_meteo_metar_parser

# Capa de proveedores METAR: la base se importa primero, luego cada
# implementación se registra mediante el decorador @register_provider.
from . import leulit_meteo_metar_provider
from . import leulit_meteo_metar_aemet
from . import leulit_meteo_metar

from . import leulit_meteo_historico
from . import leulit_meteo_config
from . import leulit_meteo_params
from . import leulit_meteo_umbral_config
