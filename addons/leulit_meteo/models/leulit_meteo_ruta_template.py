# -*- coding: utf-8 -*-

import logging
import json
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class LeulitMeteoRutaTemplate(models.Model):
    _name = 'leulit.meteo.ruta.template'
    _description = 'Plantilla de Ruta Meteorológica'
    _order = 'name'
    
    name = fields.Char(
        string='Nombre de Ruta',
        required=True,
        help='Nombre descriptivo de la ruta (ej: LEMD-LEBL, Ruta Costa)'
    )
    descripcion = fields.Text(
        string='Descripción',
        help='Descripción detallada de la ruta'
    )
    
    # Puntos de la ruta
    puntos_template_ids = fields.One2many(
        'leulit.meteo.ruta.template.punto',
        'ruta_template_id',
        string='Puntos de la Ruta'
    )
    numero_puntos = fields.Integer(
        string='Número de Puntos',
        compute='_compute_numero_puntos',
        store=True
    )
    
    # Metadatos
    activa = fields.Boolean(
        string='Activa',
        default=True,
        help='Rutas inactivas no aparecen en el selector'
    )
    color = fields.Integer(
        string='Color',
        help='Color para identificar la ruta en mapas'
    )
    
    # Estadísticas
    veces_utilizada = fields.Integer(
        string='Veces Utilizada',
        default=0,
        readonly=True
    )
    ultima_consulta = fields.Datetime(
        string='Última Consulta',
        readonly=True
    )
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Ya existe una ruta con ese nombre.')
    ]
    
    @api.depends('puntos_template_ids')
    def _compute_numero_puntos(self):
        for ruta in self:
            ruta.numero_puntos = len(ruta.puntos_template_ids)
    
    def action_aplicar_a_consulta(self):
        """Acción para aplicar esta plantilla a una nueva consulta"""
        self.ensure_one()
        
        # Crear nueva consulta
        consulta = self.env['leulit.meteo.consulta'].create({
            'ubicacion': self.name,
            'es_polilinea': True,
            'ruta_template_id': self.id,
        })
        
        # Copiar puntos
        for punto_template in self.puntos_template_ids:
            self.env['leulit.meteo.consulta.punto'].create({
                'consulta_id': consulta.id,
                'secuencia': punto_template.secuencia,
                'nombre': punto_template.nombre,
                'latitud': punto_template.latitud,
                'longitud': punto_template.longitud,
                'altitud': punto_template.altitud,
            })
        
        # Actualizar estadísticas
        self.write({
            'veces_utilizada': self.veces_utilizada + 1,
            'ultima_consulta': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'leulit.meteo.consulta',
            'res_id': consulta.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_vista_previa_mapa(self):
        """Abre vista previa de la ruta en el mapa"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/leulit_meteo/ruta_preview/{self.id}',
            'target': 'new',
        }


class LeulitMeteoRutaTemplatePunto(models.Model):
    _name = 'leulit.meteo.ruta.template.punto'
    _description = 'Punto de Plantilla de Ruta'
    _order = 'secuencia, id'
    
    ruta_template_id = fields.Many2one(
        'leulit.meteo.ruta.template',
        string='Ruta',
        required=True,
        ondelete='cascade'
    )
    
    secuencia = fields.Integer(
        string='Secuencia',
        required=True,
        default=10
    )
    nombre = fields.Char(
        string='Nombre',
        required=True,
        help='Nombre del waypoint (ej: LEMD, Waypoint 1, GOPSA)'
    )
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
        digits=(8, 2)
    )
    notas = fields.Text(string='Notas')

    display_name = fields.Char(compute='_compute_display_name', store=False)

    _sql_constraints = [
        ('secuencia_ruta_unique', 'unique(ruta_template_id, secuencia)',
         'La secuencia debe ser única dentro de cada ruta.')
    ]

    @api.depends('secuencia', 'nombre')
    def _compute_display_name(self):
        for punto in self:
            punto.display_name = f"{punto.secuencia}. {punto.nombre}"
