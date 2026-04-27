# -*- coding: utf-8 -*-

import logging
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .leulit_meteo_service import OpenMeteoService
from .leulit_meteo_windy_service import WindyService

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
    
    fuente_datos = fields.Selection([
        ('openmeteo', 'Open-Meteo'),
        ('windy', 'Windy')
    ], string='Fuente de Datos', required=True, default='openmeteo',
       help='API de donde obtener los datos meteorológicos')
    
    # Soporte para polilíneas
    es_polilinea = fields.Boolean(
        string='¿Es Polilínea?',
        default=False,
        help='Si está marcado, la consulta es para múltiples puntos (polilínea/ruta)'
    )
    ruta_template_id = fields.Many2one(
        'leulit.meteo.ruta.template',
        string='Cargar Ruta Predefinida',
        help='Selecciona una ruta guardada para cargar automáticamente sus puntos',
        domain=[('activa', '=', True)]
    )
    puntos_ids = fields.One2many(
        'leulit.meteo.consulta.punto',
        'consulta_id',
        string='Puntos de la Ruta',
        help='Puntos que conforman la polilínea'
    )
    numero_puntos = fields.Integer(
        string='Número de Puntos',
        compute='_compute_numero_puntos',
        store=True
    )
    puntos_geojson = fields.Text(
        string='Puntos (GeoJSON)',
        help='Coordenadas en formato GeoJSON para el mapa'
    )
    
    # Resumen de datos meteorológicos de la ruta
    temperatura_min = fields.Float(
        string='Temperatura Mínima (°C)',
        compute='_compute_resumen_ruta',
        store=True
    )
    temperatura_max = fields.Float(
        string='Temperatura Máxima (°C)',
        compute='_compute_resumen_ruta',
        store=True
    )
    viento_max = fields.Float(
        string='Viento Máximo (km/h)',
        compute='_compute_resumen_ruta',
        store=True
    )
    condiciones_criticas = fields.Boolean(
        string='Condiciones Críticas',
        compute='_compute_resumen_ruta',
        store=True,
        help='Hay condiciones meteorológicas adversas en la ruta'
    )
    
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
    
    @api.depends('puntos_ids')
    def _compute_numero_puntos(self):
        """Calcula el número de puntos en la polilínea"""
        for record in self:
            record.numero_puntos = len(record.puntos_ids)
    
    @api.depends('puntos_ids.temperatura', 'puntos_ids.velocidad_viento')
    def _compute_resumen_ruta(self):
        """Calcula resumen de condiciones meteorológicas de la ruta"""
        for record in self:
            if not record.puntos_ids:
                record.temperatura_min = 0
                record.temperatura_max = 0
                record.viento_max = 0
                record.condiciones_criticas = False
                continue
            
            temperaturas = record.puntos_ids.mapped('temperatura')
            temperaturas_validas = [t for t in temperaturas if t]
            
            vientos = record.puntos_ids.mapped('velocidad_viento')
            vientos_validos = [v for v in vientos if v]
            
            record.temperatura_min = min(temperaturas_validas) if temperaturas_validas else 0
            record.temperatura_max = max(temperaturas_validas) if temperaturas_validas else 0
            record.viento_max = max(vientos_validos) if vientos_validos else 0
            
            # Condiciones críticas: viento > 50 km/h o temp < 0°C
            record.condiciones_criticas = (
                record.viento_max > 50 or 
                (record.temperatura_min < 0 and record.temperatura_min != 0)
            )
    
    @api.onchange('ruta_template_id')
    def _onchange_ruta_template(self):
        """Carga puntos desde la plantilla de ruta seleccionada"""
        if self.ruta_template_id:
            # Marcar como polilínea
            self.es_polilinea = True
            
            # Actualizar nombre de ubicación
            if not self.ubicacion or self.ubicacion == 'Nueva ubicación':
                self.ubicacion = self.ruta_template_id.name
            
            # Cargar puntos (solo en creación)
            if not self.id:
                puntos_commands = []
                for punto_template in self.ruta_template_id.puntos_template_ids:
                    puntos_commands.append((0, 0, {
                        'secuencia': punto_template.secuencia,
                        'nombre': punto_template.nombre,
                        'latitud': punto_template.latitud,
                        'longitud': punto_template.longitud,
                        'altitud': punto_template.altitud,
                    }))
                self.puntos_ids = puntos_commands
    
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
    
    def action_consultar_windy(self):
        """Consulta datos desde Windy API"""
        self.ensure_one()
        
        # Obtener configuración
        api_key = self.env['ir.config_parameter'].sudo().get_param('leulit_meteo.windy_api_key')
        model = self.env['ir.config_parameter'].sudo().get_param('leulit_meteo.windy_model', 'gfs')
        
        if not api_key:
            raise UserError(_('Configure la API Key de Windy en Ajustes > Meteorología'))
        
        if self.es_polilinea and self.puntos_ids:
            # Consultar polilínea
            return self._consultar_windy_polilinea(api_key, model)
        elif self.latitud and self.longitud:
            # Consultar punto único
            return self._consultar_windy_punto(api_key, model)
        else:
            raise UserError(_('Debe especificar latitud/longitud o definir puntos de ruta'))
    
    def _consultar_windy_punto(self, api_key, model):
        """Consulta Windy para un punto único"""
        data = WindyService.get_point_forecast(self.latitud, self.longitud, api_key, model)
        
        # Actualizar campos con los datos obtenidos
        self.write({
            'fuente_datos': 'windy',
            'fecha_consulta': fields.Datetime.now(),
            'temperatura': data.get('temperatura'),
            'humedad': data.get('humedad'),
            'cobertura_nubes': data.get('cobertura_nubes'),
            'precipitacion': data.get('precipitacion'),
            'velocidad_viento': data.get('viento_velocidad'),
            'direccion_viento': data.get('viento_direccion'),
            'rachas_viento': data.get('viento_rachas'),
        })
        
        _logger.info(f'Consulta Windy actualizada: {self.codigo} - {self.ubicacion}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Datos de Windy actualizados correctamente.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _consultar_windy_polilinea(self, api_key, model):
        """Consulta Windy para múltiples puntos"""
        if not self.puntos_ids:
            raise UserError(_('Debe definir puntos para la consulta de polilínea'))
        
        # Preparar lista de coordenadas
        points = [(punto.latitud, punto.longitud) for punto in self.puntos_ids]
        
        # Consultar todos los puntos
        results = WindyService.get_polyline_forecast(points, api_key, model)
        
        # Actualizar cada punto con sus datos
        for i, punto in enumerate(self.puntos_ids):
            if i < len(results):
                data = results[i]
                if 'error' not in data:
                    punto.write({
                        'temperatura': data.get('temperatura'),
                        'humedad': data.get('humedad'),
                        'cobertura_nubes': data.get('cobertura_nubes'),
                        'precipitacion': data.get('precipitacion'),
                        'velocidad_viento': data.get('viento_velocidad'),
                        'direccion_viento': data.get('viento_direccion'),
                        'rachas_viento': data.get('viento_rachas'),
                        'datos_json': json.dumps(data),
                    })
                else:
                    punto.write({
                        'datos_json': json.dumps({'error': data.get('error')})
                    })
        
        self.write({
            'fuente_datos': 'windy',
            'fecha_consulta': fields.Datetime.now(),
        })
        
        _logger.info(f'Consulta Windy polilínea actualizada: {self.codigo} - {len(results)} puntos')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('%d puntos actualizados con datos de Windy.') % len(results),
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
    
    def action_cargar_ruta_template(self):
        """Carga puntos desde la ruta template seleccionada"""
        self.ensure_one()
        
        if not self.ruta_template_id:
            raise UserError(_('Debe seleccionar una ruta predefinida'))
        
        # Eliminar puntos existentes
        self.puntos_ids.unlink()
        
        # Crear nuevos puntos desde la plantilla
        for punto_template in self.ruta_template_id.puntos_template_ids:
            self.env['leulit.meteo.consulta.punto'].create({
                'consulta_id': self.id,
                'secuencia': punto_template.secuencia,
                'nombre': punto_template.nombre,
                'latitud': punto_template.latitud,
                'longitud': punto_template.longitud,
                'altitud': punto_template.altitud,
            })
        
        # Actualizar estadísticas de la plantilla
        self.ruta_template_id.write({
            'veces_utilizada': self.ruta_template_id.veces_utilizada + 1,
            'ultima_consulta': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Ruta Cargada'),
                'message': _('Se han cargado %d puntos de la ruta %s') % (
                    len(self.puntos_ids), self.ruta_template_id.name
                ),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_guardar_como_template(self):
        """Guarda la consulta actual como plantilla de ruta"""
        self.ensure_one()
        
        if not self.es_polilinea or not self.puntos_ids:
            raise UserError(_('Solo se pueden guardar rutas con puntos definidos'))
        
        # Crear plantilla
        template = self.env['leulit.meteo.ruta.template'].create({
            'name': self.ubicacion or f'Ruta {self.codigo}',
            'descripcion': self.notas or '',
        })
        
        # Copiar puntos
        for punto in self.puntos_ids:
            self.env['leulit.meteo.ruta.template.punto'].create({
                'ruta_template_id': template.id,
                'secuencia': punto.secuencia,
                'nombre': punto.nombre,
                'latitud': punto.latitud,
                'longitud': punto.longitud,
                'altitud': punto.altitud,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'leulit.meteo.ruta.template',
            'res_id': template.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def get_windy_embed_url(self):
        """Genera URL de embed de Windy para la consulta"""
        self.ensure_one()
        
        if self.es_polilinea and self.puntos_ids:
            # Usar centro de la ruta
            lats = self.puntos_ids.mapped('latitud')
            lons = self.puntos_ids.mapped('longitud')
            lat = sum(lats) / len(lats)
            lon = sum(lons) / len(lons)
            zoom = 7
        else:
            lat = self.latitud or 40.416
            lon = self.longitud or -3.703
            zoom = 9
        
        # URL base de Windy embed
        base_url = "https://embed.windy.com/embed2.html"
        params = [
            f"lat={lat:.3f}",
            f"lon={lon:.3f}",
            f"zoom={zoom}",
            "level=surface",
            "overlay=wind",
            "product=ecmwf",
            "menu=&message=&marker=&calendar=now",
            "pressure=&type=map",
            "location=coordinates",
            "detail=&metricWind=km/h",
            "metricTemp=°C",
        ]
        
        return f"{base_url}?{'&'.join(params)}"
