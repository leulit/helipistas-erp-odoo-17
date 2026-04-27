# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .leulit_meteo_windy_service import WindyService
from .leulit_meteo_aemet_service import AemetOpenDataService


class LeulitMeteoConfig(models.TransientModel):
    _name = 'leulit.meteo.config'
    _description = 'Configuración Meteorología'

    PARAM_WINDY_KEY = 'leulit_meteo.windy_api_key'
    PARAM_WINDY_MODEL = 'leulit_meteo.windy_model'
    PARAM_AEMET_KEY = 'leulit_meteo.aemet_api_key'

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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        res['windy_api_key'] = ICP.get_param(self.PARAM_WINDY_KEY, '')
        res['windy_model'] = ICP.get_param(self.PARAM_WINDY_MODEL, 'gfs')
        res['aemet_api_key'] = ICP.get_param(self.PARAM_AEMET_KEY, '')
        return res

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param(self.PARAM_WINDY_KEY, self.windy_api_key or '')
        ICP.set_param(self.PARAM_WINDY_MODEL, self.windy_model or 'gfs')
        ICP.set_param(self.PARAM_AEMET_KEY, self.aemet_api_key or '')
        return {'type': 'ir.actions.act_window_close'}

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
