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
        """Obtiene METAR/TAF/SIGMET del histórico y los aplica al registro."""
        self.ensure_one()
        if not self.icao_code:
            raise UserError(_('Debe indicar un código OACI.'))
        icao = self.icao_code.upper().strip()
        if len(icao) != 4 or not icao.isalpha():
            raise UserError(_(
                'El código OACI debe tener exactamente 4 letras (ej: LEMD).'))

        data = self.briefing_oaci(icao)
        if not data:
            raise UserError(_(
                'No hay datos históricos disponibles para %(icao)s. '
                'Los datos se actualizan automáticamente cada 30 minutos.'
            ) % {'icao': icao})

        self._write_observacion(data)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Briefing obtenido'),
                'message': _('METAR/TAF para %s') % icao,
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
        """Devuelve el briefing METAR/TAF/SIGMET para un OACI en una fecha.

        Fuente única de datos: siempre lee de ``leulit.meteo.historico``.
        El cron mantiene el histórico actualizado cada ~30 min.

        Resolución del OACI:
        - Si está en la tabla de referencia → usa su histórico directamente.
        - Si NO está → localiza el aeródromo de referencia más próximo
          (via coordenadas OpenAIP/CheckWX) y usa su histórico.

        Args:
            icao_code: código OACI de 4 letras.
            provider: ignorado (mantenido por compatibilidad).
            fecha: datetime UTC (o string ISO). Si None, usa la hora actual.
                   Devuelve el registro histórico más reciente con
                   ``observation_time <= fecha``.

        Returns:
            dict compatible con ``_write_observacion`` o ``None`` si no hay datos.
        """
        from .leulit_meteo_metar_parser import parse_metar

        if not icao_code:
            return None
        icao = icao_code.upper().strip()

        if fecha is None:
            fecha = fields.Datetime.now()
        elif isinstance(fecha, str):
            fecha = fields.Datetime.from_string(fecha)

        Ref = self.env['leulit.meteo.icao.reference'].sudo()
        Hist = self.env['leulit.meteo.historico'].sudo()

        # Resolver OACI → aeródromo de referencia
        ref_rec = Ref.search([('icao', '=', icao)], limit=1)
        usa_referencia = False
        ref_icao_val = ref_nombre_val = ref_distancia_km_val = fir = None

        if ref_rec:
            ref_id = ref_rec.id
            fir = ref_rec.fir
            station_name = ref_rec.nombre or icao
        else:
            nearest = Ref._resolve_nearest(icao)
            if not nearest:
                return None
            nearest_icao = nearest['icao_consultar']
            nearest_ref = Ref.search([('icao', '=', nearest_icao)], limit=1)
            if not nearest_ref:
                return None
            ref_id = nearest_ref.id
            usa_referencia = True
            ref_icao_val = nearest_icao
            ref_nombre_val = nearest['ref_nombre']
            ref_distancia_km_val = nearest['ref_distancia_km']
            fir = nearest['fir']
            station_name = nearest['ref_nombre'] or nearest_icao

        # Histórico más reciente anterior (o igual) a fecha
        hist = Hist.search([
            ('icao_reference_id', '=', ref_id),
            ('observation_time', '<=', fecha),
        ], order='observation_time desc', limit=1)

        if not hist:
            return None

        derived = parse_metar(hist.raw_metar) if hist.raw_metar else {}

        return {
            'record_id': None,
            'historico': True,
            'provider': hist.proveedor or 'aemet',
            'metar_icao': ref_icao_val or icao,
            'fuente_metar': hist.fuente_metar,
            'fuente_taf': hist.fuente_taf,
            # campos para _write_observacion
            'station_name': station_name,
            'fir_code': fir,
            'ref_icao': ref_icao_val,
            'ref_nombre': ref_nombre_val,
            'ref_distancia_km': ref_distancia_km_val,
            'usa_referencia': usa_referencia,
            'raw_metar': hist.raw_metar,
            'raw_taf': hist.raw_taf,
            'raw_sigmet': hist.raw_sigmet,
            'observation_time': hist.observation_time,
            'temperatura': derived.get('temperatura'),
            'dewpoint': derived.get('dewpoint'),
            'wind_direction': derived.get('wind_direction'),
            'wind_speed_kt': derived.get('wind_speed_kt'),
            'wind_gust_kt': derived.get('wind_gust_kt'),
            'visibility_m': derived.get('visibility_m'),
            'qnh': derived.get('qnh'),
            'humidity': None,
            'pressure': None,
            'precipitation': None,
        }

    @api.depends('icao_code', 'observation_time')
    def _compute_display_name(self):
        for record in self:
            label = record.icao_code or _('Nuevo')
            if record.observation_time:
                label += f" - {record.observation_time.strftime('%d/%m %H:%MZ')}"
            record.display_name = label
