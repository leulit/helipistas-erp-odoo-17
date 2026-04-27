# -*- coding: utf-8 -*-

from . import leulit_meteo_consulta
from . import leulit_meteo_consulta_punto
from . import leulit_meteo_ruta_template
from . import leulit_meteo_service
from . import leulit_meteo_windy_service
from . import leulit_meteo_aemet_service

# Capa de proveedores METAR: la base se importa primero, luego cada
# implementación se registra mediante el decorador @register_provider.
from . import leulit_meteo_metar_provider
from . import leulit_meteo_metar_aemet
from . import leulit_meteo_metar

from . import leulit_meteo_config
