# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .leulit_meteo_windy_service import WindyService
from .leulit_meteo_aemet_service import AemetOpenDataService


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    windy_api_key = fields.Char(
        string='Windy API Key',
        help='API Key para Windy. Obtén una en https://api.windy.com/keys',
        config_parameter='leulit_meteo.windy_api_key'
    )

    aemet_api_key = fields.Char(
        string='AEMET API Key',
        help='API Key (JWT) de AEMET OpenData. '
             'Solicítala en https://opendata.aemet.es/centrodedescargas/altaUsuario',
        config_parameter='leulit_meteo.aemet_api_key'
    )
    
    windy_model = fields.Selection([
        ('gfs', 'GFS (Global Forecast System)'),
        ('ecmwf', 'ECMWF (European Centre)'),
        ('icon', 'ICON (DWD)'),
        ('iconEu', 'ICON-EU'),
        ('nam', 'NAM (North American)'),
    ], string='Modelo Windy por Defecto',
       default='gfs',
       config_parameter='leulit_meteo.windy_model',
       help='Modelo meteorológico a usar en consultas Windy')
    
    def action_validate_windy_key(self):
        """Valida que la Windy API Key sea correcta"""
        self.ensure_one()
        if not self.windy_api_key:
            raise UserError(_('Por favor, ingrese una API Key de Windy'))
        
        if WindyService.validate_api_key(self.windy_api_key):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('¡Conexión exitosa!'),
                    'message': _('La API Key de Windy es válida.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_('La API Key de Windy no es válida. Verifique la key en https://api.windy.com/keys'))

    def action_validate_aemet_key(self):
        """Valida que la AEMET API Key sea correcta."""
        self.ensure_one()
        if not self.aemet_api_key:
            raise UserError(_('Por favor, ingrese una API Key de AEMET'))

        if AemetOpenDataService.validate_api_key(self.aemet_api_key):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('¡Conexión exitosa!'),
                    'message': _('La API Key de AEMET es válida.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_(
                'La API Key de AEMET no es válida o no responde. '
                'Compruebe la key en https://opendata.aemet.es/'))
