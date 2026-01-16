# -*- coding: utf-8 -*-

import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .leulit_meteo_metar_service import AviationWeatherService

_logger = logging.getLogger(__name__)


class LeulitMeteoMetar(models.Model):
    _name = 'leulit.meteo.metar'
    _description = 'METAR - Reporte Meteorológico Aeronáutico'
    _order = 'observation_time desc'
    _rec_name = 'icao_code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Identificación
    codigo = fields.Char(
        string='Código',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('Nuevo')
    )
    icao_code = fields.Char(
        string='Código OACI',
        required=True,
        size=4,
        help='Código OACI de 4 letras del aeródromo (ej: LECU, LEBL)',
        tracking=True
    )
    raw_metar = fields.Text(
        string='METAR Completo',
        readonly=True,
        help='Reporte METAR en formato texto original'
    )
    
    # Tiempos
    observation_time = fields.Datetime(
        string='Hora de Observación',
        readonly=True,
        help='Momento de la observación meteorológica'
    )
    report_time = fields.Datetime(
        string='Hora del Reporte',
        readonly=True,
        help='Momento de emisión del reporte'
    )
    fecha_consulta = fields.Datetime(
        string='Fecha Consulta',
        required=True,
        readonly=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    # Temperatura
    temperatura = fields.Float(
        string='Temperatura (°C)',
        digits=(5, 1),
        readonly=True,
        help='Temperatura del aire'
    )
    dewpoint = fields.Float(
        string='Punto de Rocío (°C)',
        digits=(5, 1),
        readonly=True,
        help='Temperatura del punto de rocío'
    )
    
    # Viento
    wind_direction = fields.Integer(
        string='Dirección Viento (°)',
        readonly=True,
        help='Dirección del viento en grados (0-360)'
    )
    wind_speed = fields.Float(
        string='Velocidad Viento (kt)',
        digits=(5, 1),
        readonly=True,
        help='Velocidad del viento en nudos'
    )
    wind_gust = fields.Float(
        string='Rachas (kt)',
        digits=(5, 1),
        readonly=True,
        help='Rachas de viento en nudos'
    )
    
    # Visibilidad y Presión
    visibility = fields.Float(
        string='Visibilidad (SM)',
        digits=(5, 2),
        readonly=True,
        help='Visibilidad en millas estatuarias'
    )
    altimeter = fields.Float(
        string='Altímetro (inHg)',
        digits=(5, 2),
        readonly=True,
        help='Ajuste del altímetro en pulgadas de mercurio'
    )
    qnh = fields.Float(
        string='QNH (hPa)',
        digits=(6, 1),
        readonly=True,
        help='Presión a nivel del mar en hectopascales'
    )
    
    # Categoría de Vuelo
    flight_category = fields.Selection([
        ('VFR', 'VFR - Visual Flight Rules'),
        ('MVFR', 'MVFR - Marginal VFR'),
        ('IFR', 'IFR - Instrument Flight Rules'),
        ('LIFR', 'LIFR - Low IFR'),
    ], string='Categoría de Vuelo', readonly=True, tracking=True)
    
    flight_category_desc = fields.Char(
        string='Descripción Categoría',
        compute='_compute_flight_category_desc',
        store=True
    )
    
    # Nubes y Clima
    clouds = fields.Text(
        string='Información de Nubes',
        readonly=True,
        help='Capas de nubes reportadas'
    )
    weather = fields.Char(
        string='Fenómenos Meteorológicos',
        readonly=True,
        help='Condiciones meteorológicas actuales (lluvia, niebla, etc.)'
    )
    
    # Ubicación
    latitud = fields.Float(
        string='Latitud',
        digits=(10, 6),
        readonly=True
    )
    longitud = fields.Float(
        string='Longitud',
        digits=(10, 6),
        readonly=True
    )
    elevation = fields.Float(
        string='Elevación (ft)',
        digits=(7, 0),
        readonly=True,
        help='Elevación del aeródromo en pies'
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
    
    # Relaciones
    vuelo_id = fields.Many2one(
        'leulit.vuelo',
        string='Vuelo Relacionado',
     
    
    # Campos computados para indicar frescura de datos
    edad_datos_minutos = fields.Integer(
        string='Edad de Datos (minutos)',
        compute='_compute_edad_datos',
        help='Minutos transcurridos desde la observación meteorológica'
    )
    datos_desactualizados = fields.Boolean(
        string='Datos Desactualizados',
        compute='_compute_edad_datos',
        help='Los datos tienen más de 60 minutos'
    )
    estado_datos = fields.Selection([
        ('actual', 'Actual (< 30 min)'),
        ('reciente', 'Reciente (30-60 min)'),
        ('antiguo', 'Antiguo (> 60 min)'),
    ], string='Estado de Datos', compute='_compute_edad_datos', store=True)
    
    @api.depends('observation_time')
    def _compute_edad_datos(self):
        """Calcula la edad de los datos y si están desactualizados"""
        for record in self:
            if record.observation_time:
                ahora = fields.Datetime.now()
                diferencia = ahora - record.observation_time
                minutos = int(diferencia.total_seconds() / 60)
                
                record.edad_datos_minutos = minutos
                record.datos_desactualizados = minutos > 60
                
                if minutos < 30:
                    record.estado_datos = 'actual'
                elif minutos < 60:
                    record.estado_datos = 'reciente'
                else:
                    record.estado_datos = 'antiguo'
            else:
                record.edad_datos_minutos = 0
                record.datos_desactualizados = False
                record.estado_datos = False   ondelete='set null'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Genera código de secuencia al crear"""
        for vals in vals_list:
            if vals.get('codigo', _('Nuevo')) == _('Nuevo'):
                vals['codigo'] = self.env['ir.sequence'].next_by_code('leulit.meteo.metar') or _('Nuevo')
        return super().create(vals_list)
    
    @api.depends('flight_category')
    def _compute_flight_category_desc(self):
        """Calcula descripción de la categoría de vuelo"""
        for record in self:
            if record.flight_category:
                record.flight_category_desc = AviationWeatherService.get_flight_category_description(
                    record.flight_category
                )
            else:
                record.flight_category_desc = False
    
    def action_obtener_metar(self):
        """
        Obtiene el METAR más reciente desde la API y actualiza el registro.
        
        Nota: Este método actualiza los datos del registro existente con
        el METAR más reciente disponible. Los datos anteriores se sobrescriben.
        Usa el chatter para ver el historial de cambios.
        
        Los METAR son reportes puntuales en el tiempo. Este registro almacena
        el estado del momento de la consulta (campo observation_time), no datos
        en tiempo real. Para obtener el METAR actual, ejecute este método nuevamente.
        """
        self.ensure_one()
        
        if not self.icao_code:
            raise UserError(_('Debe especificar el código OACI del aeródromo.'))
        
        # Validar formato OACI (4 letras)
        if len(self.icao_code) != 4 or not self.icao_code.isalpha():
            raise UserError(_('El código OACI debe tener exactamente 4 letras (ej: LECU, LEBL).'))
        
        # Llamar a la API
        data = AviationWeatherService.get_metar(self.icao_code)
        
        if not data:
            raise UserError(
                _('No se pudo obtener METAR para %s. Verifique el código OACI y la conexión.') % self.icao_code
            )
        
        # Actualizar campos con los datos obtenidos
        import json
        self.write({
            'fecha_consulta': fields.Datetime.now(),
            'raw_metar': data.get('raw'),
            'observation_time': data.get('observation_time'),
            'report_time': data.get('report_time'),
            'temperatura': data.get('temperature'),
            'dewpoint': data.get('dewpoint'),
            'wind_direction': data.get('wind_dir'),
            'wind_speed': data.get('wind_speed'),
            'wind_gust': data.get('wind_gust'),
            'visibility': data.get('visibility'),
            'altimeter': data.get('altimeter'),
            'qnh': data.get('qnh'),
            'flight_category': data.get('flight_category'),
            'clouds': json.dumps(data.get('clouds', []), indent=2) if data.get('clouds') else False,
            'weather': data.get('weather'),
            'latitud': data.get('latitude'),
            'longitud': data.get('longitude'),
            'elevation': data.get('elevation'),
        })
        
        _logger.info(f'METAR actualizado: {self.codigo} - {self.icao_code}')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('METAR obtenido correctamente para %s') % self.icao_code,
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def obtener_metar_aerodromo(self, icao_code):
        """
        Método helper para obtener METAR desde otros módulos
        
        Args:
            icao_code (str): Código OACI del aeródromo
            
        Returns:
            dict: Datos METAR simplificados
        """
        metar = self.create({
            'icao_code': icao_code.upper(),
        })
        
        data = AviationWeatherService.get_metar(icao_code)
        
        if data:
            import json
            metar.write({
            if record.edad_datos_minutos:
                name += f" ({record.edad_datos_minutos} min)"
            result.append((record.id, name))
        return result
    
    @api.model
    def default_get(self, fields_list):
        """Permite crear con actualización automática opcional"""
        res = super().default_get(fields_list)
        return res
    
    def write(self, vals):
        """Override write para registrar actualizaciones en el chatter"""
        result = super().write(vals)
        for record in self:
            if 'raw_metar' in vals and vals.get('raw_metar'):
                record.message_post(
                    body=_('METAR actualizado: %s') % vals['raw_metar'],
                    subject=_('Actualización METAR')
                )
        return result
    
    def actualizar_si_antiguo(self, minutos_limite=60):
        """
        Actualiza automáticamente el METAR si los datos son antiguos
        
        Args:
            minutos_limite (int): Edad máxima en minutos antes de actualizar
            
        Returns:
            bool: True si se actualizó, False si no era necesario
        """
        self.ensure_one()
        
        if not self.observation_time:
            # Sin datos, actualizar
            self.action_obtener_metar()
            return True
        
        if self.edad_datos_minutos > minutos_limite:
            _logger.info(
                f'METAR {self.icao_code} antiguo ({self.edad_datos_minutos} min), actualizando...'
            )
            self.action_obtener_metar()
            return True
        
        return Falservation_time': data.get('observation_time'),
                'report_time': data.get('report_time'),
                'temperatura': data.get('temperature'),
                'dewpoint': data.get('dewpoint'),
                'wind_direction': data.get('wind_dir'),
                'wind_speed': data.get('wind_speed'),
                'wind_gust': data.get('wind_gust'),
                'visibility': data.get('visibility'),
                'altimeter': data.get('altimeter'),
                'qnh': data.get('qnh'),
                'flight_category': data.get('flight_category'),
                'clouds': json.dumps(data.get('clouds', []), indent=2) if data.get('clouds') else False,
                'weather': data.get('weather'),
                'latitud': data.get('latitude'),
                'longitud': data.get('longitude'),
                'elevation': data.get('elevation'),
            })
            
            return {
                'metar_id': metar.id,
                'icao': metar.icao_code,
                'raw': metar.raw_metar,
                'temperatura': metar.temperatura,
                'viento_velocidad': metar.wind_speed,
                'viento_direccion': metar.wind_direction,
                'visibilidad': metar.visibility,
                'qnh': metar.qnh,
                'categoria_vuelo': metar.flight_category,
            }
        
        return None
    
    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.icao_code}"
            if record.observation_time:
                name += f" - {record.observation_time.strftime('%d/%m/%Y %H:%M')}"
            result.append((record.id, name))
        return result
