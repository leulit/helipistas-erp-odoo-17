# -*- coding: utf-8 -*-
"""Modelo genérico de reporte METAR/TAF/SIGMET.

El modelo no depende de ningún proveedor concreto: delega la obtención
de los mensajes oficiales en la instancia registrada de
:class:`MetarProvider` seleccionada en el campo ``provider``.

El **RAW** de METAR/TAF/SIGMET no se altera (legalmente importante para
AESA). Los campos numéricos decodificados son auxiliares para mostrar
una tabla; ante duda, prevalece el RAW.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .leulit_meteo_metar_provider import get_provider, provider_selection

_logger = logging.getLogger(__name__)


class LeulitMeteoMetar(models.Model):
    _name = 'leulit.meteo.metar'
    _description = 'Reporte METAR / TAF / SIGMET'
    _order = 'observation_time desc, id desc'
    _rec_name = 'icao_code'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    codigo = fields.Char(
        string='Código', readonly=True, copy=False,
        default=lambda self: _('Nuevo'))

    # Proveedor de datos
    provider = fields.Selection(
        selection=lambda self: provider_selection(),
        string='Proveedor', required=True, default='aemet', tracking=True,
        help='Origen de los datos meteorológicos.')

    # Identificación del aeródromo / estación
    icao_code = fields.Char(
        string='Código OACI', size=4, tracking=True,
        help='Código OACI de 4 letras (LEMD, LEBL, LEUL, ...).')
    station_code = fields.Char(
        string='Código de estación', tracking=True,
        help='Identificador de estación interno del proveedor. Hoy AEMET '
             'no lo usa para METAR/TAF/SIGMET; se mantiene para futuros '
             'proveedores.')
    station_name = fields.Char(string='Aeródromo', readonly=True)

    # Resolución por aeródromo de referencia
    fir_code = fields.Char(
        string='FIR', readonly=True,
        help='Región de información de vuelo (LECM, LECB, GCCC). '
             'Determina a qué FIR se piden los SIGMET.')
    ref_icao = fields.Char(
        string='OACI de referencia', readonly=True,
        help='Si el OACI introducido no emite METAR propio, se usa este '
             'aeródromo como sustituto.')
    ref_nombre = fields.Char(
        string='Nombre del aeródromo de referencia', readonly=True)
    usa_referencia = fields.Boolean(
        string='Datos de aeródromo de referencia', readonly=True)
    aviso_referencia = fields.Char(
        string='Aviso', compute='_compute_aviso_referencia')

    # Textos crudos (RAW) — fuente de verdad
    raw_metar = fields.Text(
        string='METAR', readonly=True,
        help='Texto crudo del METAR oficial publicado por AEMET. No se '
             'altera. Si el aeródromo no emite METAR propio, este texto '
             'corresponde al aeródromo de referencia.')
    raw_taf = fields.Text(
        string='TAF', readonly=True,
        help='Texto crudo del TAF oficial publicado por AEMET.')
    raw_sigmet = fields.Text(
        string='SIGMET', readonly=True,
        help='Texto crudo de los SIGMET vigentes para la FIR.')

    # Tiempos
    observation_time = fields.Datetime(
        string='Hora Observación (UTC)', readonly=True)
    fecha_consulta = fields.Datetime(
        string='Fecha Consulta', readonly=True,
        default=fields.Datetime.now)

    # Campos derivados del METAR (best-effort)
    temperatura = fields.Float(string='Temperatura (°C)', digits=(5, 1),
                               readonly=True)
    dewpoint = fields.Float(string='Punto de Rocío (°C)', digits=(5, 1),
                            readonly=True)
    humidity = fields.Float(string='Humedad Relativa (%)', digits=(5, 1),
                            readonly=True)
    wind_direction = fields.Integer(string='Dirección Viento (°)',
                                    readonly=True)
    wind_speed_kt = fields.Float(string='Velocidad Viento (kt)',
                                 digits=(5, 1), readonly=True)
    wind_gust_kt = fields.Float(string='Rachas (kt)', digits=(5, 1),
                                readonly=True)
    visibility_m = fields.Integer(string='Visibilidad (m)', readonly=True)
    qnh = fields.Float(string='QNH (hPa)', digits=(6, 1), readonly=True,
                       help='Presión a nivel del mar')
    pressure = fields.Float(string='Presión Estación (hPa)', digits=(6, 1),
                            readonly=True)
    precipitation = fields.Float(string='Precipitación (mm)', digits=(5, 1),
                                 readonly=True)

    # Ubicación (legacy, hoy AEMET no la rellena en este flujo)
    latitud = fields.Float(string='Latitud', digits=(10, 6), readonly=True)
    longitud = fields.Float(string='Longitud', digits=(10, 6), readonly=True)
    elevation = fields.Float(string='Elevación (m)', digits=(7, 0),
                             readonly=True)

    ref_distancia_km = fields.Float(
        string='Distancia Ref. (km)', digits=(6, 1), readonly=True)

    # Metadata
    user_id = fields.Many2one('res.users', string='Usuario',
                              default=lambda self: self.env.user,
                              readonly=True)
    notas = fields.Text(string='Notas')
    active = fields.Boolean(default=True)

    # Frescura de datos (computada)
    edad_datos_minutos = fields.Integer(
        string='Edad de datos (min)', compute='_compute_edad_datos')
    estado_datos = fields.Selection(
        [('actual', 'Actual (< 90 min)'),
         ('reciente', 'Reciente (90-180 min)'),
         ('antiguo', 'Antiguo (> 180 min)')],
        string='Estado de datos', compute='_compute_edad_datos', store=True)

    display_name = fields.Char(compute='_compute_display_name', store=False)

    # ---------- ORM ----------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('codigo', _('Nuevo')) == _('Nuevo'):
                vals['codigo'] = self.env['ir.sequence'].next_by_code(
                    'leulit.meteo.metar') or _('Nuevo')
            if vals.get('icao_code'):
                vals['icao_code'] = vals['icao_code'].upper().strip()
        return super().create(vals_list)

    @api.depends('observation_time')
    def _compute_edad_datos(self):
        ahora = fields.Datetime.now()
        for record in self:
            if record.observation_time:
                minutos = int(
                    (ahora - record.observation_time).total_seconds() / 60)
                record.edad_datos_minutos = minutos
                if minutos < 90:
                    record.estado_datos = 'actual'
                elif minutos < 180:
                    record.estado_datos = 'reciente'
                else:
                    record.estado_datos = 'antiguo'
            else:
                record.edad_datos_minutos = 0
                record.estado_datos = False

    @api.depends('usa_referencia', 'ref_icao', 'ref_nombre', 'icao_code')
    def _compute_aviso_referencia(self):
        for record in self:
            if record.usa_referencia and record.ref_icao:
                nombre = record.ref_nombre or record.ref_icao
                record.aviso_referencia = _(
                    'Mostrando datos de %(nombre)s (%(ref)s) porque '
                    '%(orig)s no emite METAR propio.'
                ) % {
                    'nombre': nombre,
                    'ref': record.ref_icao,
                    'orig': record.icao_code or '',
                }
            else:
                record.aviso_referencia = False

    @api.onchange('icao_code')
    def _onchange_icao_code(self):
        if self.icao_code:
            self.icao_code = self.icao_code.upper().strip()

    # ---------- Acciones de UI ----------

    def action_obtener_briefing(self):
        """Trae METAR + TAF + SIGMET del proveedor y los aplica."""
        self.ensure_one()
        if not self.icao_code:
            raise UserError(_('Debe indicar un código OACI.'))
        if len(self.icao_code) != 4 or not self.icao_code.isalpha():
            raise UserError(_(
                'El código OACI debe tener exactamente 4 letras '
                '(ej: LEMD).'))

        prov = get_provider(self.provider)
        if not prov:
            raise UserError(_(
                'Proveedor METAR no disponible: %s') % self.provider)

        data = prov.get_observation(
            self.env,
            icao_code=self.icao_code,
            station_code=self.station_code or None,
        )
        if not data:
            raise UserError(_(
                'No se han podido obtener datos del proveedor "%(prov)s" '
                'para %(icao)s. Verifique el OACI, la conexión y la '
                'configuración del proveedor.'
            ) % {'prov': prov.label, 'icao': self.icao_code})

        self._write_observacion(data)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': prov.label,
                'message': _('Briefing obtenido para %s') % self.icao_code,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                },
            },
        }

    # Alias para no romper referencias externas (XML, código de
    # terceros) que aún apunten al nombre antiguo.
    def action_obtener_metar(self):
        return self.action_obtener_briefing()

    def _write_observacion(self, data):
        """Aplica un dict normalizado del proveedor al registro."""
        self.ensure_one()
        self.write({
            'station_code': data.get('station_code') or self.station_code,
            'station_name': data.get('station_name'),
            'fir_code': data.get('fir_code'),
            'ref_icao': data.get('ref_icao'),
            'ref_nombre': data.get('ref_nombre'),
            'usa_referencia': bool(data.get('usa_referencia')),
            'raw_metar': data.get('raw_metar'),
            'raw_taf': data.get('raw_taf'),
            'raw_sigmet': data.get('raw_sigmet'),
            'observation_time': data.get('observation_time'),
            'fecha_consulta': fields.Datetime.now(),
            'temperatura': data.get('temperatura'),
            'dewpoint': data.get('dewpoint'),
            'humidity': data.get('humidity'),
            'wind_direction': data.get('wind_direction') or 0,
            'wind_speed_kt': data.get('wind_speed_kt'),
            'wind_gust_kt': data.get('wind_gust_kt'),
            'visibility_m': data.get('visibility_m') or 0,
            'qnh': data.get('qnh'),
            'pressure': data.get('pressure'),
            'precipitation': data.get('precipitation'),
            'latitud': data.get('latitude'),
            'longitud': data.get('longitude'),
            'elevation': data.get('elevation'),
            'ref_distancia_km': data.get('ref_distancia_km'),
        })

    # ---------- API reutilizable ----------

    @api.model
    def obtener_metar(self, icao_code=None, station_code=None,
                      provider='aemet', persistir=False):
        """Obtiene un briefing normalizado del proveedor indicado.

        Pensado para ser invocado desde otros módulos::

            data = self.env['leulit.meteo.metar'].obtener_metar(
                icao_code='LEUL', provider='aemet', persistir=True)

        Args:
            icao_code: código OACI del aeródromo (4 letras).
            station_code: identificador de estación interno (opcional).
            provider: código del proveedor registrado (por defecto
                ``aemet``).
            persistir: si ``True``, crea un registro y añade
                ``record_id`` al dict devuelto.

        Returns:
            dict con el esquema normalizado documentado en
            :mod:`leulit_meteo_metar_provider`, o ``None``.
        """
        if not icao_code:
            return None
        prov = get_provider(provider)
        if not prov:
            raise UserError(_(
                'Proveedor METAR no disponible: %s') % provider)

        data = prov.get_observation(
            self.env,
            icao_code=icao_code.upper().strip(),
            station_code=(station_code or '').strip() or None,
        )
        if not data:
            return None

        if persistir:
            record = self.create({
                'provider': provider,
                'icao_code': icao_code.upper().strip(),
                'station_code': data.get('station_code'),
            })
            record._write_observacion(data)
            data['record_id'] = record.id
        return data

    @api.model
    def briefing_oaci(self, icao_code, provider='aemet', fecha=None):
        """Busca o crea el reporte METAR para el OACI y devuelve el briefing.

        Reutilizable desde cualquier módulo::

            # Datos actuales
            result = self.env['leulit.meteo.metar'].briefing_oaci('LEUL')

            # Datos históricos (busca en BD, no llama a la API)
            from datetime import datetime
            result = self.env['leulit.meteo.metar'].briefing_oaci(
                'LEUL', fecha=datetime(2026, 4, 27, 14, 30))

        Args:
            icao_code: código OACI de 4 letras (ej. 'LEUL').
            provider: proveedor a usar si se crea el registro. Solo se aplica
                en modo actual; ignorado en modo histórico.
            fecha: datetime UTC opcional. Si se indica y corresponde a más de
                30 minutos en el pasado, activa el **modo histórico**: busca
                en la BD el registro con ``observation_time`` más cercano a
                esa fecha (máx. 2 horas de diferencia) sin llamar a la API.
                Las APIs de los proveedores no ofrecen datos históricos.

        Returns:
            dict con claves:
                - ``record_id`` (int)
                - ``raw_metar`` (str|None)
                - ``raw_taf`` (str|None)
                - ``raw_metar_est`` (str|None)
                - ``historico`` (bool) — True si viene de la BD sin actualizar
                - ``observation_time`` (datetime UTC|None)
                - ``provider`` (str) — proveedor usado ('aemet', 'checkwx', ...)
                - ``metar_icao`` (str) — OACI del que procede el METAR/TAF
                - ``usa_referencia`` (bool) — True si metar_icao ≠ icao_code
            o ``None`` si no hay datos disponibles.
        """
        if not icao_code:
            return None
        icao = icao_code.upper().strip()

        # ── Modo histórico ──────────────────────────────────────────────────
        if fecha is not None:
            from datetime import timedelta
            if isinstance(fecha, str):
                fecha = fields.Datetime.from_string(fecha)
            ahora = fields.Datetime.now()
            if (ahora - fecha) > timedelta(minutes=30):
                # 1. Buscar en histórico automático (leulit.meteo.historico)
                Hist = self.env['leulit.meteo.historico']
                hist = Hist.search([
                    ('icao', '=', icao),
                    ('observation_time', '<=', fecha),
                ], order='observation_time desc', limit=1)
                if not hist:
                    hist = Hist.search([
                        ('icao', '=', icao),
                        ('observation_time', '>=', fecha),
                    ], order='observation_time asc', limit=1)
                if hist and hist.observation_time:
                    diff_seg = abs((hist.observation_time - fecha).total_seconds())
                    if diff_seg <= 7200:
                        return {
                            'record_id': None,
                            'raw_metar': hist.raw_metar,
                            'raw_taf': hist.raw_taf,
                            'raw_metar_est': None,
                            'raw_sigmet': hist.raw_sigmet,
                            'historico': True,
                            'observation_time': hist.observation_time,
                            'provider': hist.proveedor or 'aemet',
                            'metar_icao': hist.ref_icao if hist.usa_referencia else hist.icao,
                            'usa_referencia': hist.usa_referencia,
                            'fuente_metar': hist.fuente_metar,
                            'fuente_taf': hist.fuente_taf,
                        }

                # 2. Fallback: buscar en reportes manuales (leulit.meteo.metar)
                record = self.search([
                    ('icao_code', '=', icao),
                    ('active', '=', True),
                    ('observation_time', '<=', fecha),
                ], order='observation_time desc', limit=1)
                if not record:
                    record = self.search([
                        ('icao_code', '=', icao),
                        ('active', '=', True),
                        ('observation_time', '>=', fecha),
                    ], order='observation_time asc', limit=1)
                if not record or not record.observation_time:
                    return None
                diff_seg = abs((record.observation_time - fecha).total_seconds())
                if diff_seg > 7200:
                    return None
                return {
                    'record_id': record.id,
                    'raw_metar': record.raw_metar,
                    'raw_taf': record.raw_taf,
                    'raw_metar_est': record.raw_metar_est,
                    'historico': True,
                    'observation_time': record.observation_time,
                    'provider': record.provider,
                    'metar_icao': record.ref_icao if record.usa_referencia else record.icao_code,
                    'usa_referencia': record.usa_referencia,
                }

        # ── Modo actual: busca/crea registro y llama a la API ───────────────
        record = self.search(
            [('icao_code', '=', icao), ('active', '=', True)],
            order='fecha_consulta desc',
            limit=1,
        )
        if not record:
            record = self.create({'provider': provider, 'icao_code': icao})

        prov = get_provider(record.provider)
        if not prov:
            raise UserError(
                _('Proveedor METAR no disponible: %s') % record.provider)

        data = prov.get_observation(self.env, icao_code=icao)
        if not data:
            return None

        record._write_observacion(data)

        return {
            'record_id': record.id,
            'raw_metar': record.raw_metar,
            'raw_taf': record.raw_taf,
            'raw_metar_est': record.raw_metar_est,
            'historico': False,
            'observation_time': record.observation_time,
            'provider': record.provider,
            'metar_icao': record.ref_icao if record.usa_referencia else record.icao_code,
            'usa_referencia': record.usa_referencia,
        }

    @api.depends('icao_code', 'observation_time')
    def _compute_display_name(self):
        for record in self:
            label = record.icao_code or _('Nuevo')
            if record.observation_time:
                label += f" - {record.observation_time.strftime('%d/%m %H:%MZ')}"
            record.display_name = label
