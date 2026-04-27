# -*- coding: utf-8 -*-
"""Modelo genérico de reporte METAR.

El modelo no depende de ningún proveedor concreto: delega la obtención
de la observación en la instancia registrada de :class:`MetarProvider`
seleccionada en el campo ``provider``. Para añadir un nuevo proveedor,
crear un fichero en ``models/`` que defina una subclase de
``MetarProvider`` registrada con ``@register_provider`` e importarlo en
``models/__init__.py``.
"""

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .leulit_meteo_metar_provider import (
    get_provider, provider_selection,
)

_logger = logging.getLogger(__name__)


class LeulitMeteoMetar(models.Model):
    _name = 'leulit.meteo.metar'
    _description = 'Reporte METAR'
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
        help='Origen de los datos meteorológicos. Cada proveedor implementa '
             'la interfaz MetarProvider y se selecciona aquí.')

    # Identificación del aeródromo / estación
    icao_code = fields.Char(
        string='Código OACI', size=4, tracking=True,
        help='Código OACI de 4 letras (LEMD, LEBL, GCLP...). '
             'Algunos proveedores lo usan para resolver el código de '
             'estación interno.')
    station_code = fields.Char(
        string='Código de estación', tracking=True,
        help='Identificador de la estación dentro del proveedor (p. ej. '
             'IDEMA en AEMET). Si se rellena, prevalece sobre el OACI.')
    station_name = fields.Char(string='Estación', readonly=True)

    # Texto METAR
    raw_metar = fields.Text(
        string='METAR', readonly=True,
        help='Texto en formato METAR. Algunos proveedores (p. ej. AEMET) '
             'lo sintetizan a partir de la observación horaria; en ese caso '
             'el texto incluye el sufijo "RMK <PROVEEDOR>".')

    # Tiempos
    observation_time = fields.Datetime(
        string='Hora Observación (UTC)', readonly=True)
    fecha_consulta = fields.Datetime(
        string='Fecha Consulta', readonly=True,
        default=fields.Datetime.now)

    # Magnitudes meteorológicas (esquema normalizado del proveedor)
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

    # Ubicación
    latitud = fields.Float(string='Latitud', digits=(10, 6), readonly=True)
    longitud = fields.Float(string='Longitud', digits=(10, 6), readonly=True)
    elevation = fields.Float(string='Elevación (m)', digits=(7, 0),
                             readonly=True)

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

    @api.onchange('icao_code', 'provider')
    def _onchange_icao_code(self):
        if self.icao_code:
            self.icao_code = self.icao_code.upper().strip()
        prov = get_provider(self.provider) if self.provider else None
        if prov and self.icao_code and not self.station_code:
            # Solo dict estático en onchange (no red): la resolución
            # completa ocurre al pulsar "Obtener observación".
            sc = prov.prefill_station_code(self.icao_code)
            if sc:
                self.station_code = sc

    # ---------- Acciones de UI ----------

    def action_obtener_metar(self):
        """Refresca el registro con la última observación del proveedor."""
        self.ensure_one()
        if not self.icao_code and not self.station_code:
            raise UserError(_(
                'Debe indicar un código OACI o un código de estación.'))
        if self.icao_code and (
                len(self.icao_code) != 4 or not self.icao_code.isalpha()):
            raise UserError(_(
                'El código OACI debe tener exactamente 4 letras (ej: LEMD).'))

        prov = get_provider(self.provider)
        if not prov:
            raise UserError(_(
                'Proveedor METAR no disponible: %s') % self.provider)

        # Auto-resolución agresiva: si el usuario solo introdujo OACI,
        # pedimos al proveedor que resuelva el station_code interno
        # (dict estático + inventario AEMET, según implemente cada uno).
        if self.icao_code and not self.station_code:
            sc = prov.resolve(self.env, self.icao_code)
            if sc:
                self.station_code = sc
            else:
                msg = _(
                    'No se ha podido resolver automáticamente la estación '
                    'para OACI %(icao)s en el proveedor "%(prov)s".'
                ) % {'icao': self.icao_code, 'prov': prov.label}
                if self.provider == 'aemet':
                    msg += '\n\n' + _(
                        'Use el botón "Buscar estación AEMET" para '
                        'localizar el indicativo (IDEMA) por nombre/'
                        'provincia y aplicarlo manualmente.')
                raise UserError(msg)

        data = prov.get_observation(
            self.env,
            icao_code=self.icao_code or None,
            station_code=self.station_code or None,
        )
        if not data:
            msg = _(
                'No se han podido obtener datos del proveedor "%(prov)s" '
                'para %(ref)s. Verifique el código OACI/estación, la '
                'conexión y la configuración del proveedor.'
            ) % {
                'prov': prov.label,
                'ref': self.icao_code or self.station_code,
            }
            if self.provider == 'aemet' and not self.station_code:
                msg += '\n\n' + _(
                    'Sugerencia: AEMET puede no tener mapeado este OACI. '
                    'Use el botón "Buscar estación AEMET" para localizar '
                    'el indicativo (IDEMA) por nombre/provincia y '
                    'aplicarlo al campo "Código de estación".')
            raise UserError(msg)

        self._write_observacion(data)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': prov.label,
                'message': _('Observación obtenida para %s') % (
                    self.icao_code or self.station_code),
                'type': 'success',
                'sticky': False,
            },
        }

    def _write_observacion(self, data):
        """Aplica un dict normalizado del proveedor al registro."""
        self.ensure_one()
        self.write({
            'station_code': data.get('station_code') or self.station_code,
            'station_name': data.get('station_name'),
            'raw_metar': data.get('raw_metar'),
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
        })

    # ---------- API reutilizable ----------

    @api.model
    def obtener_metar(self, icao_code=None, station_code=None,
                      provider='aemet', persistir=False):
        """Obtiene una observación normalizada del proveedor indicado.

        Pensado para ser invocado desde otros módulos::

            data = self.env['leulit.meteo.metar'].obtener_metar(
                icao_code='LEMD', provider='aemet')

        Args:
            icao_code: código OACI del aeródromo.
            station_code: identificador de estación interno del proveedor.
            provider: código del proveedor registrado (por defecto ``aemet``).
            persistir: si ``True``, crea/actualiza un registro y añade
                ``record_id`` al dict devuelto.

        Returns:
            dict con el esquema normalizado documentado en
            :mod:`leulit_meteo_metar_provider`, o ``None``.
        """
        if not icao_code and not station_code:
            return None
        prov = get_provider(provider)
        if not prov:
            raise UserError(_(
                'Proveedor METAR no disponible: %s') % provider)

        data = prov.get_observation(
            self.env,
            icao_code=(icao_code or '').upper().strip() or None,
            station_code=(station_code or '').strip() or None,
        )
        if not data:
            return None

        if persistir:
            record = self.create({
                'provider': provider,
                'icao_code': (icao_code or '').upper().strip() or False,
                'station_code': data.get('station_code'),
            })
            record._write_observacion(data)
            data['record_id'] = record.id
        return data

    def action_buscar_estacion_aemet(self):
        """Abre el wizard ``leulit.meteo.aemet.station.finder`` apuntando
        a este registro, para que el usuario seleccione manualmente la
        estación cuando ``resolve_idema`` no consigue mapear el OACI."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Buscar estación AEMET'),
            'res_model': 'leulit.meteo.aemet.station.finder',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_metar_id': self.id,
                'default_search_term': self.icao_code or '',
            },
        }

    @api.depends('icao_code', 'station_code', 'observation_time')
    def _compute_display_name(self):
        for record in self:
            label = record.icao_code or record.station_code or _('Nuevo')
            if record.observation_time:
                label += f" - {record.observation_time.strftime('%d/%m %H:%MZ')}"
            record.display_name = label
