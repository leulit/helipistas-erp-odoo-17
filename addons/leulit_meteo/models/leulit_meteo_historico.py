# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    @api.depends('icao', 'observation_time')
    def _compute_display_name(self):
        for record in self:
            label = record.icao or '?'
            if record.observation_time:
                label += f" - {record.observation_time.strftime('%d/%m %H:%MZ')}"
            record.display_name = label
