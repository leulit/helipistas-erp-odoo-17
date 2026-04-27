# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class LeulitMeteoConsultaPunto(models.Model):
    _name = 'leulit.meteo.consulta.punto'
    _description = 'Punto de Consulta Meteorológica'
    _order = 'secuencia, id'
    
    # Relación con la consulta
    consulta_id = fields.Many2one(
        'leulit.meteo.consulta',
        string='Consulta',
        required=True,
        ondelete='cascade'
    )
    
    # Identificación del punto
    secuencia = fields.Integer(
        string='Secuencia',
        required=True,
        default=0,
        help='Orden del punto en la polilínea'
    )
    nombre = fields.Char(
        string='Nombre del Punto',
        help='Identificador o nombre del punto (ej: Waypoint 1, Madrid, etc.)'
    )
    
    # Coordenadas
    latitud = fields.Float(
        string='Latitud',
        required=True,
        digits=(10, 6)
    )
    longitud = fields.Float(
        string='Longitud',
        required=True,
        digits=(10, 6)
    )
    altitud = fields.Float(
        string='Altitud (m)',
        digits=(8, 2),
        help='Altitud en metros sobre el nivel del mar (opcional)'
    )
    
    # Datos meteorológicos del punto
    temperatura = fields.Float(
        string='Temperatura (°C)',
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
    cobertura_nubes = fields.Float(
        string='Cobertura de Nubes (%)',
        digits=(5, 2),
        readonly=True
    )
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
    presion = fields.Float(
        string='Presión (hPa)',
        digits=(7, 2),
        readonly=True
    )
    visibilidad = fields.Float(
        string='Visibilidad (km)',
        digits=(5, 2),
        readonly=True
    )
    
    # Datos completos en JSON
    datos_json = fields.Text(
        string='Datos Completos (JSON)',
        readonly=True,
        help='Respuesta completa de la API en formato JSON'
    )
    
    # Metadata
    notas = fields.Text(string='Notas')

    display_name = fields.Char(compute='_compute_display_name', store=False)

    _sql_constraints = [
        ('secuencia_consulta_unique', 'unique(consulta_id, secuencia)',
         'La secuencia debe ser única dentro de cada consulta.')
    ]
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-asignar secuencia si no se proporciona"""
        for vals in vals_list:
            if 'secuencia' not in vals or vals['secuencia'] == 0:
                consulta_id = vals.get('consulta_id')
                if consulta_id:
                    # Obtener la siguiente secuencia
                    max_seq = self.search([
                        ('consulta_id', '=', consulta_id)
                    ], order='secuencia desc', limit=1)
                    vals['secuencia'] = (max_seq.secuencia + 1) if max_seq else 1
        return super().create(vals_list)
    
    @api.depends('secuencia', 'nombre', 'latitud', 'longitud')
    def _compute_display_name(self):
        """Nombre descriptivo del punto"""
        for punto in self:
            if punto.nombre:
                punto.display_name = f"Punto {punto.secuencia}: {punto.nombre}"
            else:
                punto.display_name = f"Punto {punto.secuencia} ({punto.latitud}, {punto.longitud})"
