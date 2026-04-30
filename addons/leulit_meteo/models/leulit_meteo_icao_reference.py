# -*- coding: utf-8 -*-
import logging
import math
import traceback as _traceback

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from .leulit_meteo_notifier import meteo_notify_error

_logger = logging.getLogger(__name__)

_TZ_MADRID = 'Europe/Madrid'


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fir_heuristic(lat, lon):
    """FIR por heurística de coordenadas cuando no hay registro en tabla."""
    if lat is not None and lat <= 30:
        return 'GCCC'
    if lat is not None and lon is not None and lon >= -1.5 and lat >= 40:
        return 'LECB'
    return 'LECM'


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

    # Coordenadas
    latitud = fields.Float('Latitud', digits=(10, 6))
    longitud = fields.Float('Longitud', digits=(10, 6))
    elevacion_ft = fields.Integer('Elevación (ft AMSL)')

    # Proveedor del METAR oficial
    proveedor_oficial = fields.Selection([
        ('aemet', 'AEMET'),
        ('checkwx', 'CheckWX'),
        ('ninguno', 'Ninguno'),
    ], string='Proveedor METAR oficial', default='aemet')

    proxima_actualizacion = fields.Datetime(
        'Próxima actualización (UTC)', readonly=True,
        help='Momento estimado en que se espera el siguiente METAR. '
             'El cron solo procesa este aeródromo cuando la hora actual '
             'es igual o posterior a este valor.')
    proxima_actualizacion_utc = fields.Char(
        'Próxima actualización (UTC)', compute='_compute_proxima_actualizacion_local',
        readonly=True)
    proxima_actualizacion_local = fields.Char(
        'Próxima actualización (Madrid)', compute='_compute_proxima_actualizacion_local',
        readonly=True)

    ultima_ejecucion_cron = fields.Datetime(
        'Última ejecución cron (UTC)', readonly=True,
        help='Momento en que el cron procesó por última vez este aeródromo, '
             'independientemente del resultado.')
    ultima_ejecucion_cron_local = fields.Char(
        'Última ejecución cron (Madrid)', compute='_compute_ultima_ejecucion_local',
        readonly=True)

    notas = fields.Text()

    historico_count = fields.Integer(
        'Registros históricos', compute='_compute_historico_count')

    historico_ids = fields.One2many(
        'leulit.meteo.historico', 'icao_reference_id',
        string='Histórico METAR/TAF')

    _sql_constraints = [
        ('icao_uniq', 'UNIQUE(icao)', 'Ya existe un mapeo para este OACI.'),
    ]

    def _compute_historico_count(self):
        for rec in self:
            rec.historico_count = self.env['leulit.meteo.historico'].search_count(
                [('icao_reference_id', '=', rec.id)])

    @api.depends('proxima_actualizacion')
    def _compute_proxima_actualizacion_local(self):
        tz = pytz.timezone(_TZ_MADRID)
        for rec in self:
            if rec.proxima_actualizacion:
                rec.proxima_actualizacion_utc = rec.proxima_actualizacion.strftime('%d/%m/%Y %H:%MZ')
                dt = rec.proxima_actualizacion.replace(tzinfo=pytz.utc).astimezone(tz)
                rec.proxima_actualizacion_local = dt.strftime('%d/%m/%Y %H:%M %Z')
            else:
                rec.proxima_actualizacion_utc = False
                rec.proxima_actualizacion_local = False

    @api.depends('ultima_ejecucion_cron')
    def _compute_ultima_ejecucion_local(self):
        tz = pytz.timezone(_TZ_MADRID)
        for rec in self:
            if rec.ultima_ejecucion_cron:
                dt = rec.ultima_ejecucion_cron.replace(tzinfo=pytz.utc).astimezone(tz)
                rec.ultima_ejecucion_cron_local = dt.strftime('%d/%m/%Y %H:%M %Z')
            else:
                rec.ultima_ejecucion_cron_local = False

    # ---------- Acciones UI ----------

    def action_ver_historico(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Histórico METAR/TAF - {self.icao}',
            'res_model': 'leulit.meteo.historico',
            'view_mode': 'tree,form',
            'domain': [('icao_reference_id', '=', self.id)],
            'context': {'default_icao_reference_id': self.id},
        }

    # ---------- Cron ----------

    @api.model
    def action_actualizar_metar_cron(self):
        """Cron cada 10 min: procesa solo los aeródromos cuya próxima actualización ya ha llegado."""
        from datetime import timedelta
        from .leulit_meteo_metar_provider import get_provider

        prov = get_provider('aemet')
        if not prov:
            _logger.error("Cron METAR: proveedor 'aemet' no disponible")
            meteo_notify_error(
                self.env,
                'Cron METAR — registro de proveedores',
                RuntimeError("El proveedor 'aemet' no está registrado. "
                             "Verifica que el módulo leulit_meteo esté correctamente instalado."),
                contexto={'Proveedor requerido': 'aemet',
                          'Método': 'action_actualizar_metar_cron'},
            )
            return

        ahora = fields.Datetime.now()
        refs = self.search([
            '|',
            ('proxima_actualizacion', '=', False),
            ('proxima_actualizacion', '<=', ahora),
        ])
        if not refs:
            return

        _logger.info("Cron METAR: %d aeródromo(s) pendientes de actualización", len(refs))
        Historico = self.env['leulit.meteo.historico']
        errores = []

        for ref in refs:
            ref.sudo().write({'ultima_ejecucion_cron': ahora})
            try:
                data = prov.get_observation(self.env, icao_code=ref.icao)
                if not data:
                    _logger.warning("Cron METAR: sin datos para %s", ref.icao)
                    # Evitar bucle infinito: reintentar en 10 min aunque no haya datos.
                    ref.sudo().write({'proxima_actualizacion': ahora + timedelta(minutes=10)})
                    continue

                obs_time = data.get('observation_time')

                if obs_time:
                    existe = Historico.search([
                        ('icao_reference_id', '=', ref.id),
                        ('observation_time', '=', obs_time),
                    ], limit=1)
                    if existe:
                        # Si obs_time + 35min ya está en el pasado (AEMET no ha emitido
                        # nuevo METAR aún), reintentar en 5 min para no quedar bloqueados.
                        proxima = obs_time + timedelta(minutes=35)
                        if proxima <= ahora:
                            proxima = ahora + timedelta(minutes=5)
                        ref.sudo().write({'proxima_actualizacion': proxima})
                        _logger.debug(
                            "Cron METAR: %s sin cambios (%s), próxima a las %s",
                            ref.icao, obs_time, proxima.strftime('%H:%MZ'))
                        continue

                provider_code = data.get('provider') or 'aemet'
                Historico.create({
                    'icao_reference_id': ref.id,
                    'icao_consultar': data.get('icao_consultar') or ref.icao,
                    'raw_metar': data.get('raw_metar'),
                    'raw_taf': data.get('raw_taf'),
                    'raw_sigmet': data.get('raw_sigmet'),
                    'observation_time': obs_time,
                    'fecha_obtencion': ahora,
                    'fuente_metar': provider_code if data.get('raw_metar') else 'ninguno',
                    'fuente_taf': provider_code if data.get('raw_taf') else 'ninguno',
                    'usa_referencia': bool(data.get('usa_referencia')),
                    'ref_icao': data.get('ref_icao'),
                    'ref_nombre': data.get('ref_nombre'),
                    'proveedor': provider_code,
                })

                if obs_time:
                    proxima = obs_time + timedelta(minutes=35)
                    ref.sudo().write({'proxima_actualizacion': proxima})
                    _logger.info(
                        "Cron METAR: histórico guardado para %s (%s), próxima a las %s",
                        ref.icao, obs_time, proxima.strftime('%H:%MZ'))
                else:
                    _logger.info("Cron METAR: histórico guardado para %s (sin obs_time)", ref.icao)

            except Exception as exc:
                tb_str = _traceback.format_exc()
                _logger.error("Cron METAR: error en %s: %s", ref.icao, exc)
                errores.append((ref.icao, str(exc), tb_str))
                ref.sudo().write({'proxima_actualizacion': ahora + timedelta(minutes=10)})

        if errores:
            self._cron_notificar_errores(errores)

    @api.model
    def _cron_notificar_errores(self, errores):
        """Envía email con los errores del cron al email configurado en Parámetros.

        Cada elemento de ``errores`` es una tupla ``(icao, error_msg, traceback_str)``.
        """
        email_to = self.env['ir.config_parameter'].sudo().get_param(
            'leulit_meteo.email_errores', '')
        if not email_to:
            return

        def _esc(s):
            return (str(s)
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;'))

        ahora = fields.Datetime.now().strftime('%d/%m/%Y %H:%M UTC')

        filas = ''
        for item in errores:
            icao = item[0]
            error_msg = item[1]
            tb_str = item[2] if len(item) > 2 else None

            tb_html = ''
            if tb_str:
                tb_html = (
                    '<details style="margin-top:6px;">'
                    '<summary style="cursor:pointer;color:#666;font-size:11px;">'
                    '&#9656; Traceback completo</summary>'
                    '<pre style="background:#f8f8f8;border:1px solid #eee;padding:8px;'
                    'font-size:10px;font-family:monospace;margin:4px 0 0;'
                    'white-space:pre-wrap;word-break:break-all;">'
                    + _esc(tb_str) + '</pre></details>'
                )

            filas += (
                f'<tr>'
                f'<td style="padding:6px 12px;border:1px solid #ddd;vertical-align:top;'
                f'white-space:nowrap;">{_esc(icao)}</td>'
                f'<td style="padding:6px 12px;border:1px solid #ddd;vertical-align:top;'
                f'color:#b00;">{_esc(error_msg)}{tb_html}</td>'
                f'</tr>'
            )

        body = f"""
<div style="font-family:sans-serif;max-width:720px;">
  <div style="background:#b00;color:#fff;padding:10px 18px;border-radius:4px 4px 0 0;">
    <strong>Errores en actualizaci&#243;n autom&#225;tica de METAR</strong>
  </div>
  <div style="border:1px solid #ddd;border-top:none;padding:16px 18px;background:#fff;">
    <p style="margin:0 0 12px;">
      La tarea de actualizaci&#243;n autom&#225;tica de METAR ({ahora})
      ha encontrado errores en <strong>{len(errores)}</strong> aer&#243;dromo(s):
    </p>
    <table style="border-collapse:collapse;width:100%;margin-bottom:12px;">
      <thead>
        <tr style="background:#f5f5f5;">
          <th style="padding:6px 12px;border:1px solid #ddd;text-align:left;">OACI</th>
          <th style="padding:6px 12px;border:1px solid #ddd;text-align:left;">Error</th>
        </tr>
      </thead>
      <tbody>{filas}</tbody>
    </table>
  </div>
  <div style="padding:8px 18px;background:#f5f5f5;border:1px solid #ddd;border-top:none;
              font-size:11px;color:#888;border-radius:0 0 4px 4px;">
    Mensaje autom&#225;tico del m&#243;dulo de Meteorolog&#237;a (leulit_meteo).
  </div>
</div>"""

        try:
            self.env['mail.mail'].sudo().create({
                'subject': (
                    f'[METAR] Errores en actualización automática '
                    f'({len(errores)} aeródromo(s))'
                ),
                'body_html': body,
                'email_to': email_to,
                'auto_delete': True,
            }).send()
            _logger.info("Cron METAR: notificación de errores enviada a %s", email_to)
        except Exception as exc:
            _logger.error("Cron METAR: fallo al enviar notificación de errores: %s", exc)

    # ---------- Sincronización CheckWX ----------

    @api.model
    def action_sincronizar_desde_checkwx(self):
        """Descarga la lista oficial de estaciones METAR de España (CheckWX) y sincroniza la tabla.

        Solo procesa estaciones con ICAO prefijo LE* o GC* y country_code ES.
        Crea/actualiza registros. Elimina los que ya no aparecen en CheckWX.
        """
        from .leulit_meteo_checkwx_service import CheckWXService

        ICP = self.env['ir.config_parameter'].sudo()
        checkwx_key = ICP.get_param('leulit_meteo.checkwx_api_key', '')
        if not checkwx_key:
            raise UserError(_('Configura primero la API Key de CheckWX en Configuración → API Keys.'))

        if not CheckWXService.validate_api_key(checkwx_key):
            raise UserError(_(
                'La API Key de CheckWX no es válida o no hay conexión con el servicio.\n'
                'Comprueba la key en Configuración → API Keys y que tengas acceso a internet.'))

        candidatos_es = CheckWXService.get_stations_by_country('ES', checkwx_key)

        estaciones = {}
        sin_prefijo = 0
        for c in candidatos_es:
            icao = (c.get('icao') or '').upper().strip()
            if not (icao.startswith('LE') or icao.startswith('GC')):
                sin_prefijo += 1
                continue
            if icao not in estaciones:
                estaciones[icao] = {
                    'nombre': (c.get('name') or icao).strip(),
                    'lat': float(c.get('lat') or 0.0),
                    'lon': float(c.get('lon') or 0.0),
                    'elevation_ft': c.get('elevation_ft') or 0,
                }

        _logger.info(
            "CheckWX sync: %d candidatos ES, %d con prefijo LE/GC, %d descartados por prefijo",
            len(candidatos_es), len(estaciones), sin_prefijo)

        if not estaciones:
            raise UserError(_(
                'CheckWX devolvió %d estaciones para ES pero ninguna con prefijo LE* o GC*.\n'
                'Revisa los logs del servidor para más detalle.') % len(candidatos_es))

        _logger.info("CheckWX sync: %d estaciones españolas encontradas", len(estaciones))

        creados = actualizados = 0

        for icao, info in estaciones.items():
            lat = info['lat']
            lon = info['lon']
            fir = _fir_heuristic(lat or None, lon or None)

            rec = self.search([('icao', '=', icao)], limit=1)
            vals = {
                'nombre': info['nombre'],
                'fir': fir,
                'latitud': lat,
                'longitud': lon,
                'elevacion_ft': info.get('elevation_ft') or 0,
                'proveedor_oficial': 'aemet',
            }
            if rec:
                rec.sudo().write(vals)
                actualizados += 1
            else:
                self.sudo().create({'icao': icao, 'proxima_actualizacion': False, **vals})
                creados += 1

        icao_oficiales = set(estaciones.keys())
        obsoletos = self.search([('icao', 'not in', list(icao_oficiales))])
        borrados = len(obsoletos)
        obsoletos.sudo().unlink()

        _logger.info(
            "CheckWX sync completado: %d creados, %d actualizados, %d eliminados",
            creados, actualizados, borrados)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Aeródromos de referencia actualizados'),
                'message': _('%d añadidos · %d actualizados · %d eliminados') % (
                    creados, actualizados, borrados),
                'type': 'success',
                'sticky': True,
            },
        }

    # ---------- Sincronización AviationWeather.gov ----------

    @api.model
    def action_sincronizar_desde_aviationweather(self):
        """Obtiene estaciones LE*/GC* con METAR o TAF desde aviationweather.gov (sin API key).

        Crea/actualiza registros. Elimina los que ya no aparecen en la fuente.
        """
        from .leulit_meteo_aviation_weather_service import AviationWeatherService

        estaciones = AviationWeatherService.get_stations_spain()

        if not estaciones:
            raise UserError(_(
                'aviationweather.gov no devolvió ninguna estación española con METAR o TAF.\n'
                'Comprueba la conexión a internet y vuelve a intentarlo.'))

        _logger.info(
            "AviationWeather sync: %d estaciones LE*/GC* con METAR/TAF encontradas",
            len(estaciones))

        creados = actualizados = 0

        for icao, info in estaciones.items():
            lat = info['lat']
            lon = info['lon']
            fir = _fir_heuristic(lat or None, lon or None)

            rec = self.search([('icao', '=', icao)], limit=1)
            vals = {
                'nombre': info['nombre'],
                'fir': fir,
                'latitud': lat,
                'longitud': lon,
                'elevacion_ft': info.get('elevation_ft') or 0,
                'proveedor_oficial': 'aemet',
            }
            if rec:
                rec.sudo().write(vals)
                actualizados += 1
            else:
                self.sudo().create({'icao': icao, 'proxima_actualizacion': False, **vals})
                creados += 1

        icao_oficiales = set(estaciones.keys())
        obsoletos = self.search([('icao', 'not in', list(icao_oficiales))])
        borrados = len(obsoletos)
        obsoletos.sudo().unlink()

        _logger.info(
            "AviationWeather sync completado: %d creados, %d actualizados, %d eliminados",
            creados, actualizados, borrados)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Aeródromos de referencia actualizados'),
                'message': _('%d añadidos · %d actualizados · %d eliminados') % (
                    creados, actualizados, borrados),
                'type': 'success',
                'sticky': True,
            },
        }

    # ---------- API pública ----------

    @api.model
    def resolve(self, icao):
        """Devuelve dict de resolución para icao.

        Si el ICAO está en la tabla lo devuelve directamente.
        Si no está, busca el aeródromo de referencia más próximo usando
        coordenadas obtenidas de OpenAIP (o CheckWX como fallback).
        """
        if not icao:
            return None
        icao_up = icao.upper().strip()
        rec = self.search([('icao', '=', icao_up)], limit=1)
        if rec:
            return {
                'icao_consultar': rec.icao,
                'fir': rec.fir,
                'usa_referencia': False,
                'nombre': rec.nombre,
                'ref_nombre': None,
                'ref_distancia_km': None,
                'proveedor_oficial': rec.proveedor_oficial or 'aemet',
                'latitud': rec.latitud or None,
                'longitud': rec.longitud or None,
            }
        return self._resolve_nearest(icao_up)

    @api.model
    def _resolve_nearest(self, icao, lat=None, lon=None, exclude_icao=None):
        """Encuentra el aeródromo de referencia más próximo al ICAO dado.

        Si lat/lon no se proporcionan, los obtiene via OpenAIP (fallback CheckWX).
        No crea ningún registro nuevo.
        exclude_icao: ICAO a excluir del resultado (para evitar devolver el mismo).
        """
        if lat is None or lon is None:
            from .leulit_meteo_openaip_service import OpenAIPService
            from .leulit_meteo_checkwx_service import CheckWXService

            ICP = self.env['ir.config_parameter'].sudo()
            openaip_key = ICP.get_param('leulit_meteo.openaip_api_key', '')
            checkwx_key = ICP.get_param('leulit_meteo.checkwx_api_key', '')

            if openaip_key:
                info = OpenAIPService.get_airport_by_icao(icao, openaip_key)
                if info:
                    lat = info.get('lat')
                    lon = info.get('lon')

            if (lat is None) and checkwx_key:
                station_info = CheckWXService.get_station(icao, checkwx_key)
                if station_info:
                    lat = station_info.get('lat')
                    lon = station_info.get('lon')

        if lat is None:
            _logger.warning("_resolve_nearest %s: no se obtuvieron coordenadas", icao)
            return None

        domain = [('latitud', '!=', 0.0), ('longitud', '!=', 0.0)]
        if exclude_icao:
            domain.append(('icao', '!=', exclude_icao.upper()))
        all_refs = self.search(domain)
        best = None
        best_dist = float('inf')
        for ref in all_refs:
            dist = _haversine(lat, lon, ref.latitud, ref.longitud)
            if dist < best_dist:
                best_dist = dist
                best = ref

        if not best:
            _logger.warning("_resolve_nearest %s: no hay aeródromos con coordenadas en tabla", icao)
            return None

        _logger.info(
            "_resolve_nearest %s → %s (%.1f km)", icao, best.icao, best_dist)
        return {
            'icao_consultar': best.icao,
            'fir': best.fir,
            'usa_referencia': True,
            'nombre': icao,
            'ref_nombre': best.nombre or best.icao,
            'ref_distancia_km': round(best_dist, 1),
            'proveedor_oficial': best.proveedor_oficial or 'aemet',
            'latitud': lat,
            'longitud': lon,
        }
