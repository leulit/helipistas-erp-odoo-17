# -*- coding: utf-8 -*-
"""Tabla de aeródromos / helipuertos de referencia OACI <-> FIR.

Sirve para dos cosas:

1. Saber a qué FIR consultar SIGMET (LECM Madrid, LECB Barcelona,
   GCCC Canarias).
2. Mapear aeródromos sin METAR propio (helipuertos pequeños) al
   aeródromo de referencia con METAR/TAF más cercano.

El registro contiene los puntos operados por la organización; el
administrador los mantiene desde el menú **Meteorología -> Aeródromos
de Referencia**.
"""

from odoo import api, fields, models


class LeulitMeteoIcaoReference(models.Model):
    _name = 'leulit.meteo.icao.reference'
    _description = 'Aeródromos de referencia OACI / FIR'
    _rec_name = 'icao'
    _order = 'icao'

    icao = fields.Char('OACI', size=4, required=True, index=True)
    nombre = fields.Char('Nombre del punto')
    fir = fields.Selection([
        ('LECM', 'LECM - Madrid'),
        ('LECB', 'LECB - Barcelona'),
        ('GCCC', 'GCCC - Canarias'),
    ], string='FIR', required=True)
    tiene_metar_propio = fields.Boolean(
        'Emite METAR propio', default=True,
        help='Si está desmarcado, usaremos el aeródromo de referencia '
             'para METAR/TAF.')
    ref_icao = fields.Char(
        'OACI de referencia', size=4,
        help='Aeródromo con METAR/TAF que usaremos cuando este punto no '
             'emita.')
    ref_nombre = fields.Char('Nombre del aeródromo de referencia')
    notas = fields.Text()

    _sql_constraints = [
        ('icao_uniq', 'UNIQUE(icao)',
         'Ya existe un mapeo para este OACI.'),
    ]

    @api.model
    def resolve(self, icao):
        """Devuelve dict de resolución, o ``None`` si no hay match.

        Claves del dict:
            * ``icao_consultar`` (str): OACI a usar contra AEMET para
              METAR/TAF (puede ser el propio o el de referencia).
            * ``fir`` (str): código de FIR.
            * ``usa_referencia`` (bool): True si se usa el aeródromo de
              referencia.
            * ``nombre`` (str): nombre del punto original.
            * ``ref_nombre`` (str|None): nombre del aeródromo de
              referencia, o ``None``.
        """
        if not icao:
            return None
        rec = self.search([('icao', '=', icao.upper())], limit=1)
        if not rec:
            return None
        if not rec.tiene_metar_propio and rec.ref_icao:
            return {
                'icao_consultar': rec.ref_icao.upper(),
                'fir': rec.fir,
                'usa_referencia': True,
                'nombre': rec.nombre,
                'ref_nombre': rec.ref_nombre or rec.ref_icao,
            }
        return {
            'icao_consultar': rec.icao,
            'fir': rec.fir,
            'usa_referencia': False,
            'nombre': rec.nombre,
            'ref_nombre': None,
        }
