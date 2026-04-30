# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .leulit_meteo_windy_service import WindyService
from .leulit_meteo_aemet_service import AemetOpenDataService
from .leulit_meteo_checkwx_service import CheckWXService
from .leulit_meteo_openaip_service import OpenAIPService
from .leulit_meteo_aviation_weather_service import AviationWeatherService


class LeulitMeteoConfig(models.TransientModel):
    _name = 'leulit.meteo.config'
    _description = 'Configuración Meteorología'

    PARAM_WINDY_KEY = 'leulit_meteo.windy_api_key'
    PARAM_WINDY_MODEL = 'leulit_meteo.windy_model'
    PARAM_AEMET_KEY = 'leulit_meteo.aemet_api_key'
    PARAM_OPENAIP_KEY = 'leulit_meteo.openaip_api_key'
    PARAM_CHECKWX_KEY = 'leulit_meteo.checkwx_api_key'
    PARAM_AVIATION_WEATHER_KEY = 'leulit_meteo.aviation_weather_api_key'

    windy_api_key = fields.Char(
        string='Windy API Key',
        help='API Key para Windy. Obtenerla en https://api.windy.com/keys')
    windy_model = fields.Selection([
        ('gfs', 'GFS (Global Forecast System)'),
        ('ecmwf', 'ECMWF (European Centre)'),
        ('icon', 'ICON (DWD)'),
        ('iconEu', 'ICON-EU'),
        ('nam', 'NAM (North American)'),
    ], string='Modelo Windy por Defecto', default='gfs')
    aemet_api_key = fields.Char(
        string='AEMET OpenData API Key',
        help='API Key (JWT) de AEMET OpenData. '
             'Solicítala en https://opendata.aemet.es/centrodedescargas/altaUsuario')
    openaip_api_key = fields.Char(
        string='OpenAIP API Key',
        help='API Key de OpenAIP para resolución de aeródromos por OACI y '
             'búsqueda por proximidad. Regístrate en https://www.openaip.net/')
    checkwx_api_key = fields.Char(
        string='CheckWX API Key',
        help='API Key de CheckWX para METAR/TAF/Station de aeródromos '
             'internacionales. Regístrate en https://www.checkwxapi.com/')
    aviation_weather_api_key = fields.Char(
        string='Aviation Weather API Key (opcional)',
        help='La API de aviationweather.gov (NOAA/FAA) es pública y no requiere '
             'clave. Déjalo vacío para usar el acceso público gratuito.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        res['windy_api_key'] = ICP.get_param(self.PARAM_WINDY_KEY, '')
        res['windy_model'] = ICP.get_param(self.PARAM_WINDY_MODEL, 'gfs')
        res['aemet_api_key'] = ICP.get_param(self.PARAM_AEMET_KEY, '')
        res['openaip_api_key'] = ICP.get_param(self.PARAM_OPENAIP_KEY, '')
        res['checkwx_api_key'] = ICP.get_param(self.PARAM_CHECKWX_KEY, '')
        res['aviation_weather_api_key'] = ICP.get_param(self.PARAM_AVIATION_WEATHER_KEY, '')
        return res

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param(self.PARAM_WINDY_KEY, self.windy_api_key or '')
        ICP.set_param(self.PARAM_WINDY_MODEL, self.windy_model or 'gfs')
        ICP.set_param(self.PARAM_AEMET_KEY, self.aemet_api_key or '')
        ICP.set_param(self.PARAM_OPENAIP_KEY, self.openaip_api_key or '')
        ICP.set_param(self.PARAM_CHECKWX_KEY, self.checkwx_api_key or '')
        ICP.set_param(self.PARAM_AVIATION_WEATHER_KEY, self.aviation_weather_api_key or '')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Guardado'),
                'message': _('API Keys guardadas correctamente.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_validate_windy_key(self):
        self.ensure_one()
        if not self.windy_api_key:
            raise UserError(_('Introduce primero una API Key de Windy.'))
        if WindyService.validate_api_key(self.windy_api_key):
            return self._notify(_('Windy'), _('La API Key de Windy es válida.'), 'success')
        raise UserError(_('La API Key de Windy no es válida.'))

    def action_validate_aemet_key(self):
        self.ensure_one()
        if not self.aemet_api_key:
            raise UserError(_('Introduce primero una API Key de AEMET.'))
        if AemetOpenDataService.validate_api_key(self.aemet_api_key):
            return self._notify(_('AEMET'), _('La API Key de AEMET es válida.'), 'success')
        raise UserError(_('La API Key de AEMET no es válida o no responde.'))

    def action_validate_openaip_key(self):
        self.ensure_one()
        if not self.openaip_api_key:
            raise UserError(_('Introduce primero una API Key de OpenAIP.'))
        result = OpenAIPService.get_airport_by_icao('LEMD', self.openaip_api_key)
        if result:
            return self._notify(_('OpenAIP'), _('La API Key de OpenAIP es válida.'), 'success')
        raise UserError(_('La API Key de OpenAIP no es válida o no responde.'))

    def action_validate_checkwx_key(self):
        self.ensure_one()
        if not self.checkwx_api_key:
            raise UserError(_('Introduce primero una API Key de CheckWX.'))
        if CheckWXService.validate_api_key(self.checkwx_api_key):
            return self._notify(_('CheckWX'), _('La API Key de CheckWX es válida.'), 'success')
        raise UserError(_('La API Key de CheckWX no es válida o no responde.'))

    def action_validate_aviation_weather(self):
        self.ensure_one()
        if AviationWeatherService.validate():
            return self._notify(
                _('Aviation Weather'),
                _('aviationweather.gov responde correctamente. Servicio disponible.'),
                'success')
        raise UserError(_('No se pudo conectar con aviationweather.gov. Comprueba la conexión a internet.'))

    def _notify(self, title, message, kind):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': kind,
                'sticky': False,
            },
        }
