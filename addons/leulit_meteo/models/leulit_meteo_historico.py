# -*- coding: utf-8 -*-
import logging

import pytz

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_TZ_MADRID = 'Europe/Madrid'


class LeulitMeteoHistorico(models.Model):
    _name = 'leulit.meteo.historico'
    _description = 'Histórico METAR/TAF por aeródromo de referencia'
    _order = 'fecha_obtencion desc, id desc'
    _rec_name = 'icao'

    icao_reference_id = fields.Many2one(
        'leulit.meteo.icao.reference',
        string='Aeródromo de referencia',
        ondelete='cascade', index=True, required=True)
    icao = fields.Char(
        related='icao_reference_id.icao', store=True, index=True,
        string='OACI')
    icao_consultar = fields.Char(
        string='OACI consultado',
        help='OACI realmente consultado; puede diferir del OACI del aeródromo '
             'cuando éste no emite METAR propio y se usa uno de referencia.')

    raw_metar = fields.Text('METAR RAW', readonly=True)
    raw_taf = fields.Text('TAF RAW', readonly=True)
    raw_sigmet = fields.Text('SIGMET RAW', readonly=True)

    observation_time = fields.Datetime('Hora Observación (UTC)', readonly=True)
    fecha_obtencion = fields.Datetime(
        'Fecha Obtención', default=fields.Datetime.now, readonly=True, index=True)

    fuente_metar = fields.Selection([
        ('aemet', 'AEMET'),
        ('checkwx', 'CheckWX'),
        ('ninguno', 'Sin datos'),
    ], string='Fuente METAR', default='ninguno')
    fuente_taf = fields.Selection([
        ('aemet', 'AEMET'),
        ('checkwx', 'CheckWX'),
        ('ninguno', 'Sin datos'),
    ], string='Fuente TAF', default='ninguno')

    usa_referencia = fields.Boolean('Datos de aeródromo de referencia', readonly=True)
    ref_icao = fields.Char('OACI Referencia', readonly=True)
    ref_nombre = fields.Char('Nombre Referencia', readonly=True)
    proveedor = fields.Char('Proveedor', readonly=True)

    edad_datos = fields.Char(
        string='Actualización', compute='_compute_edad_datos',
        help='Tiempo transcurrido desde la observación.')
    observation_time_utc = fields.Char(
        string='Observación (UTC)', compute='_compute_tiempos_local',
        help='Hora de observación en UTC (formato explícito).')
    observation_time_local = fields.Char(
        string='Observación (Madrid)', compute='_compute_tiempos_local',
        help='Hora de observación en hora local de Madrid.')
    fecha_obtencion_utc = fields.Char(
        string='Obtenido (UTC)', compute='_compute_tiempos_local',
        help='Fecha de obtención en UTC (formato explícito).')
    fecha_obtencion_local = fields.Char(
        string='Obtenido (Madrid)', compute='_compute_tiempos_local',
        help='Fecha de obtención en hora local de Madrid.')

    @api.depends('observation_time')
    def _compute_edad_datos(self):
        ahora = fields.Datetime.now()
        for rec in self:
            if rec.observation_time:
                minutos = int((ahora - rec.observation_time).total_seconds() / 60)
                if minutos < 1:
                    rec.edad_datos = 'Ahora mismo'
                elif minutos < 60:
                    rec.edad_datos = f'Hace {minutos} min'
                else:
                    horas = minutos // 60
                    mins = minutos % 60
                    rec.edad_datos = f'Hace {horas}h {mins:02d}min' if mins else f'Hace {horas}h'
            else:
                rec.edad_datos = False

    @api.depends('observation_time', 'fecha_obtencion')
    def _compute_tiempos_local(self):
        tz = pytz.timezone(_TZ_MADRID)
        for rec in self:
            if rec.observation_time:
                rec.observation_time_utc = rec.observation_time.strftime('%d/%m/%Y %H:%MZ')
                dt = rec.observation_time.replace(tzinfo=pytz.utc).astimezone(tz)
                rec.observation_time_local = dt.strftime('%d/%m/%Y %H:%M %Z')
            else:
                rec.observation_time_utc = False
                rec.observation_time_local = False
            if rec.fecha_obtencion:
                rec.fecha_obtencion_utc = rec.fecha_obtencion.strftime('%d/%m/%Y %H:%MZ')
                dt = rec.fecha_obtencion.replace(tzinfo=pytz.utc).astimezone(tz)
                rec.fecha_obtencion_local = dt.strftime('%d/%m/%Y %H:%M %Z')
            else:
                rec.fecha_obtencion_utc = False
                rec.fecha_obtencion_local = False

    @api.depends('icao', 'observation_time')
    def _compute_display_name(self):
        tz = pytz.timezone(_TZ_MADRID)
        for record in self:
            label = record.icao or '?'
            if record.observation_time:
                utc_str = record.observation_time.strftime('%d/%m %H:%MZ')
                dt_local = record.observation_time.replace(tzinfo=pytz.utc).astimezone(tz)
                local_str = dt_local.strftime('%H:%M %Z')
                label += f" - {utc_str} ({local_str})"
            record.display_name = label
