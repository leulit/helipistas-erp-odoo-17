# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .leulit_meteo_service import OpenMeteoService

_logger = logging.getLogger(__name__)


class LeulitMeteoConsulta(models.Model):
    _name = 'leulit.meteo.consulta'
    _description = 'Consulta Meteorológica'
    _order = 'fecha_consulta desc'
    _rec_name = 'ubicacion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Campos básicos
    codigo = fields.Char(
        string='Código',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('Nuevo')
    )
    ubicacion = fields.Char(
        string='Ubicación',
        required=True,
        help='Nombre de la ubicación (ej: Madrid, LECU - Cuatro Vientos)'
    )
    latitud = fields.Float(
        string='Latitud',
        required=True,
        digits=(10, 6),
        help='Latitud en grados decimales'
    )
    longitud = fields.Float(
        string='Longitud',
        required=True,
        digits=(10, 6),
        help='Longitud en grados decimales'
    )
    fecha_consulta = fields.Datetime(
        string='Fecha Consulta',
        required=True,
        readonly=True,
        default=fields.Datetime.now
    )
    tipo_consulta = fields.Selection([
        ('actual', 'Clima Actual'),
        ('pronostico', 'Pronóstico')
    ], string='Tipo', required=True, default='actual')
    
    # Datos meteorológicos actuales
    temperatura = fields.Float(
        string='Temperatura (°C)',
        digits=(5, 2),
        readonly=True
    )
    sensacion_termica = fields.Float(
        string='Sensación Térmica (°C)',
        digits=(5, 2),
        readonly=True
    )
    humedad = fields.Float(
        string='Humedad Relativa (%)',
        digits=(5, 2),
        readonly=True
    )
    precipitacion = fields.Float(
        string='Precipitación (mm)',
        digits=(5, 2),
        readonly=True
    )
    codigo_clima = fields.Integer(
        string='Código Clima WMO',
        readonly=True
    )
    descripcion_clima = fields.Char(
        string='Condiciones',
        compute='_compute_descripcion_clima',
        store=True
    )
    cobertura_nubes = fields.Float(
        string='Cobertura de Nubes (%)',
        digits=(5, 2),
        readonly=True
    )
    
    # Viento
    velocidad_viento = fields.Float(
        string='Velocidad Viento (km/h)',
        digits=(5, 2),
        readonly=True
    )
    direccion_viento = fields.Float(
        string='Dirección Viento (°)',
        digits=(5, 2),
        readonly=True
    )
    rachas_viento = fields.Float(
        string='Rachas de Viento (km/h)',
        digits=(5, 2),
        readonly=True
    )
    
    # Datos del pronóstico
    datos_pronostico = fields.Text(
        string='Datos Pronóstico JSON',
        readonly=True,
        help='Datos completos del pronóstico en formato JSON'
    )
    
    # Metadata
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        default=lambda self: self.env.user,
        readonly=True
    )
    notas = fields.Text(string='Notas')
    active = fields.Boolean(default=True)
    
    # Campos relacionados (opcionales para futuras integraciones)
    vuelo_id = fields.Many2one(
        'leulit.vuelo',
        string='Vuelo Relacionado',
        ondelete='set null'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Genera código de secuencia al crear"""
        for vals in vals_list:
            if vals.get('codigo', _('Nuevo')) == _('Nuevo'):
                vals['codigo'] = self.env['ir.sequence'].next_by_code('leulit.meteo.consulta') or _('Nuevo')
        return super().create(vals_list)
    
    @api.depends('codigo_clima')
    def _compute_descripcion_clima(self):
        """Calcula la descripción del clima basada en el código WMO"""
        for record in self:
            if record.codigo_clima:
                record.descripcion_clima = OpenMeteoService.get_weather_description(record.codigo_clima)
            else:
                record.descripcion_clima = False
    
    def action_consultar_clima_actual(self):
        """Consulta el clima actual desde la API"""
        self.ensure_one()
        
        if not self.latitud or not self.longitud:
            raise UserError(_('Debe especificar latitud y longitud para realizar la consulta.'))
        
        # Llamar a la API
        data = OpenMeteoService.get_current_weather(self.latitud, self.longitud)
        
        if not data or 'current' not in data:
            raise UserError(_('No se pudo obtener información meteorológica. Verifique la conexión a internet y los datos de ubicación.'))
        
        # Actualizar campos con los datos obtenidos
        current = data['current']
        self.write({
            'tipo_consulta': 'actual',
            'fecha_consulta': fields.Datetime.now(),
            'temperatura': current.get('temperature_2m'),
            'sensacion_termica': current.get('apparent_temperature'),
            'humedad': current.get('relative_humidity_2m'),
            'precipitacion': current.get('precipitation', 0.0),
            'codigo_clima': current.get('weather_code'),
            'cobertura_nubes': current.get('cloud_cover'),
            'velocidad_viento': current.get('wind_speed_10m'),
            'direccion_viento': current.get('wind_direction_10m'),
            'rachas_viento': current.get('wind_gusts_10m'),
        })
        
        _logger.info(f'Consulta meteorológica actualizada: {self.codigo} - {self.ubicacion}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Datos meteorológicos actualizados correctamente.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_consultar_pronostico(self):
        """Consulta el pronóstico meteorológico desde la API"""
        self.ensure_one()
        
        if not self.latitud or not self.longitud:
            raise UserError(_('Debe especificar latitud y longitud para realizar la consulta.'))
        
        # Llamar a la API
        data = OpenMeteoService.get_forecast(self.latitud, self.longitud, days=7)
        
        if not data or 'daily' not in data:
            raise UserError(_('No se pudo obtener el pronóstico meteorológico. Verifique la conexión a internet y los datos de ubicación.'))
        
        # Guardar los datos del pronóstico como JSON
        import json
        self.write({
            'tipo_consulta': 'pronostico',
            'fecha_consulta': fields.Datetime.now(),
            'datos_pronostico': json.dumps(data, indent=2),
        })
        
        _logger.info(f'Pronóstico meteorológico obtenido: {self.codigo} - {self.ubicacion}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Pronóstico meteorológico obtenido correctamente.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def consultar_clima_ubicacion(self, ubicacion, latitud, longitud):
        """
        Método helper para consultar clima desde otros módulos
        
        Args:
            ubicacion (str): Nombre de la ubicación
            latitud (float): Latitud
            longitud (float): Longitud
            
        Returns:
            dict: Datos meteorológicos
        """
        consulta = self.create({
            'ubicacion': ubicacion,
            'latitud': latitud,
            'longitud': longitud,
            'tipo_consulta': 'actual',
        })
        
        data = OpenMeteoService.get_current_weather(latitud, longitud)
        
        if data and 'current' in data:
            current = data['current']
            consulta.write({
                'temperatura': current.get('temperature_2m'),
                'sensacion_termica': current.get('apparent_temperature'),
                'humedad': current.get('relative_humidity_2m'),
                'precipitacion': current.get('precipitation', 0.0),
                'codigo_clima': current.get('weather_code'),
                'cobertura_nubes': current.get('cloud_cover'),
                'velocidad_viento': current.get('wind_speed_10m'),
                'direccion_viento': current.get('wind_direction_10m'),
                'rachas_viento': current.get('wind_gusts_10m'),
            })
            
            return {
                'consulta_id': consulta.id,
                'temperatura': consulta.temperatura,
                'descripcion': consulta.descripcion_clima,
                'viento': consulta.velocidad_viento,
                'humedad': consulta.humedad,
            }
        
        return None
