# -*- coding: utf-8 -*-
import logging
import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Radio máximo en km para buscar aeródromo con METAR cerca de un OACI desconocido
_SEARCH_RADIUS_KM = 150


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
    tiene_metar_propio = fields.Boolean(
        'Emite METAR propio', default=True,
        help='Si está desmarcado, usaremos el aeródromo de referencia '
             'para METAR/TAF.')
    ref_icao = fields.Char(
        'OACI de referencia', size=4,
        help='Aeródromo con METAR/TAF que usaremos cuando este punto no emita.')
    ref_nombre = fields.Char('Nombre del aeródromo de referencia')
    ref_distancia_km = fields.Float(
        'Distancia al aeródromo ref. (km)', digits=(6, 1))

    # Coordenadas del OACI (rellenas en auto-resolución)
    latitud = fields.Float('Latitud', digits=(10, 6))
    longitud = fields.Float('Longitud', digits=(10, 6))

    # Estación AEMET convencional más próxima
    station_code = fields.Char('Cód. Estación AEMET', size=10)
    station_nombre = fields.Char('Estación AEMET')
    station_distancia_km = fields.Float(
        'Distancia estación (km)', digits=(6, 1))

    # Proveedor del METAR oficial
    proveedor_oficial = fields.Selection([
        ('aemet', 'AEMET'),
        ('checkwx', 'CheckWX'),
        ('ninguno', 'Ninguno'),
    ], string='Proveedor METAR oficial', default='aemet')

    auto_resolved = fields.Boolean(
        'Auto-resuelto', default=False, readonly=True,
        help='True si este registro fue creado automáticamente por el '
             'sistema al encontrar un OACI desconocido.')

    proxima_actualizacion = fields.Datetime(
        'Próxima actualización (UTC)', readonly=True,
        help='Momento estimado en que se espera el siguiente METAR. '
             'El cron solo procesa este aeródromo cuando la hora actual '
             'es igual o posterior a este valor.')

    notas = fields.Text()

    historico_count = fields.Integer(
        'Registros históricos', compute='_compute_historico_count')

    _sql_constraints = [
        ('icao_uniq', 'UNIQUE(icao)', 'Ya existe un mapeo para este OACI.'),
    ]

    def _compute_historico_count(self):
        for rec in self:
            rec.historico_count = self.env['leulit.meteo.historico'].search_count(
                [('icao_reference_id', '=', rec.id)])

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
            return

        ahora = fields.Datetime.now()
        # Solo aeródromos que nunca se han actualizado o cuya próxima actualización ya pasó
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
            try:
                data = prov.get_observation(self.env, icao_code=ref.icao)
                if not data:
                    _logger.warning("Cron METAR: sin datos para %s", ref.icao)
                    # Reintentar en 10 min (próxima ejecución del cron)
                    continue

                obs_time = data.get('observation_time')

                # Evitar duplicados con mismo observation_time
                if obs_time:
                    existe = Historico.search([
                        ('icao_reference_id', '=', ref.id),
                        ('observation_time', '=', obs_time),
                    ], limit=1)
                    if existe:
                        # METAR no ha cambiado; posponer próxima comprobación 15 min
                        ref.sudo().write({
                            'proxima_actualizacion': obs_time + timedelta(minutes=35),
                        })
                        _logger.debug(
                            "Cron METAR: %s sin cambios (%s), próxima a las %s",
                            ref.icao, obs_time,
                            (obs_time + timedelta(minutes=35)).strftime('%H:%MZ'))
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

                # Calcular próxima actualización: obs_time + 30 min (ciclo METAR) + 5 min margen
                if obs_time:
                    proxima = obs_time + timedelta(minutes=35)
                    ref.sudo().write({'proxima_actualizacion': proxima})
                    _logger.info(
                        "Cron METAR: histórico guardado para %s (%s), próxima a las %s",
                        ref.icao, obs_time, proxima.strftime('%H:%MZ'))
                else:
                    _logger.info("Cron METAR: histórico guardado para %s (sin obs_time)", ref.icao)

            except Exception as exc:
                _logger.error("Cron METAR: error en %s: %s", ref.icao, exc)
                errores.append((ref.icao, str(exc)))

        if errores:
            self._cron_notificar_errores(errores)

    @api.model
    def _cron_notificar_errores(self, errores):
        """Envía email de notificación de errores del cron al email configurado en Parámetros."""
        email_to = self.env['ir.config_parameter'].sudo().get_param(
            'leulit_meteo.email_errores', '')
        if not email_to:
            return

        ahora = fields.Datetime.now().strftime('%d/%m/%Y %H:%M UTC')
        filas = ''.join(
            f'<tr>'
            f'<td style="padding:6px 12px;border:1px solid #ddd;">{icao}</td>'
            f'<td style="padding:6px 12px;border:1px solid #ddd;color:#c00;">{error}</td>'
            f'</tr>'
            for icao, error in errores
        )
        body = f"""
            <p>La tarea de actualización automática de METAR
            ({ahora}) ha encontrado errores en
            <strong>{len(errores)}</strong> aeródromo(s):</p>
            <table style="border-collapse:collapse;margin:12px 0;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:6px 12px;border:1px solid #ddd;">OACI</th>
                        <th style="padding:6px 12px;border:1px solid #ddd;">Error</th>
                    </tr>
                </thead>
                <tbody>{filas}</tbody>
            </table>
            <p style="color:#888;font-size:12px;">
                Mensaje automático del módulo de Meteorología.
            </p>
        """
        try:
            self.env['mail.mail'].sudo().create({
                'subject': f'[METAR] Errores en actualización automática ({len(errores)} aeródromo(s))',
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

        Usa dos llamadas por radio desde CheckWX:
          · Centro Península + Baleares  (40.0, -3.7)  r=400 nm
          · Canarias                     (28.1, -15.4) r=200 nm
        Solo procesa estaciones con ICAO prefijo LE* o GC* y country_code ES.

        Lógica BD:
        - Crea registros nuevos con tiene_metar_propio=True y proxima_actualizacion=None
          (el cron los procesa en su siguiente ejecución).
        - Actualiza nombre y coordenadas de los ya existentes con tiene_metar_propio=True.
        - No toca registros con tiene_metar_propio=False (helipuertos / refs manuales).
        - Elimina los tiene_metar_propio=True que ya no aparecen en CheckWX.
        """
        from .leulit_meteo_checkwx_service import CheckWXService

        ICP = self.env['ir.config_parameter'].sudo()
        checkwx_key = ICP.get_param('leulit_meteo.checkwx_api_key', '')
        if not checkwx_key:
            raise UserError(_('Configura primero la API Key de CheckWX en Configuración → API Keys.'))

        # Validar la API Key antes de intentar la sincronización completa
        if not CheckWXService.validate_api_key(checkwx_key):
            raise UserError(_(
                'La API Key de CheckWX no es válida o no hay conexión con el servicio.\n'
                'Comprueba la key en Configuración → API Keys y que tengas acceso a internet.'))

        # Obtener todas las estaciones españolas (LE* y GC*) directamente por país.
        # Se usa el endpoint /v2/station/country/ES, que devuelve estaciones registradas
        # independientemente de si tienen METAR activo en este momento. Esto es más fiable
        # que buscar por radio, que solo devuelve aeródromos con METAR activo y tiene
        # un límite de resultados que puede excluir aeródromos peninsulares.
        candidatos_es = CheckWXService.get_stations_by_country('ES', checkwx_key)

        estaciones = {}   # icao -> {nombre, lat, lon}
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
                }

        _logger.info(
            "CheckWX sync: %d candidatos ES, %d con prefijo LE/GC, %d descartados por prefijo",
            len(candidatos_es), len(estaciones), sin_prefijo)

        if not estaciones:
            raise UserError(_(
                'CheckWX devolvió %d estaciones para ES pero ninguna con prefijo LE* o GC*.\n'
                'Revisa los logs del servidor para más detalle.') % len(candidatos_es))

        _logger.info("CheckWX sync: %d estaciones españolas encontradas", len(estaciones))

        # Sincronizar BD
        creados = actualizados = 0

        for icao, info in estaciones.items():
            lat = info['lat']
            lon = info['lon']
            fir = _fir_heuristic(lat or None, lon or None)

            rec = self.search([('icao', '=', icao)], limit=1)
            vals = {
                'nombre': info['nombre'],
                'fir': fir,
                'tiene_metar_propio': True,
                'latitud': lat,
                'longitud': lon,
                'proveedor_oficial': 'aemet',
                'auto_resolved': False,
            }
            if rec:
                if not rec.tiene_metar_propio:
                    continue   # helipuerto / ref manual — no tocar
                rec.sudo().write(vals)
                actualizados += 1
            else:
                # proxima_actualizacion=False → el cron lo procesará en su próxima ejecución
                self.sudo().create({'icao': icao, 'proxima_actualizacion': False, **vals})
                creados += 1

        # Eliminar los que ya no están en la lista oficial
        icao_oficiales = set(estaciones.keys())
        obsoletos = self.search([
            ('tiene_metar_propio', '=', True),
            ('icao', 'not in', list(icao_oficiales)),
        ])
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

    # ---------- API pública ----------

    @api.model
    def resolve(self, icao):
        """Devuelve dict de resolución para icao, auto-creando el registro si no existe."""
        if not icao:
            return None
        icao_up = icao.upper().strip()
        rec = self.search([('icao', '=', icao_up)], limit=1)
        if not rec:
            rec = self._auto_resolve(icao_up)
        if not rec:
            return None

        ref_entry = {
            'station_code': rec.station_code or None,
            'station_nombre': rec.station_nombre or None,
            'station_distancia_km': rec.station_distancia_km or None,
            'ref_distancia_km': rec.ref_distancia_km or None,
            'latitud': rec.latitud or None,
            'longitud': rec.longitud or None,
        }

        if not rec.tiene_metar_propio and rec.ref_icao:
            return {
                'icao_consultar': rec.ref_icao.upper(),
                'fir': rec.fir,
                'usa_referencia': True,
                'nombre': rec.nombre,
                'ref_nombre': rec.ref_nombre or rec.ref_icao,
                'proveedor_oficial': rec.proveedor_oficial or 'aemet',
                **ref_entry,
            }
        return {
            'icao_consultar': rec.icao,
            'fir': rec.fir,
            'usa_referencia': False,
            'nombre': rec.nombre,
            'ref_nombre': None,
            'proveedor_oficial': rec.proveedor_oficial or 'aemet',
            **ref_entry,
        }

    # ---------- Auto-resolución ----------

    @api.model
    def _auto_resolve(self, icao):
        """Intenta crear un registro para icao consultando OpenAIP + CheckWX + AEMET."""
        from .leulit_meteo_openaip_service import OpenAIPService
        from .leulit_meteo_checkwx_service import CheckWXService
        from .leulit_meteo_aemet_service import AemetOpenDataService

        ICP = self.env['ir.config_parameter'].sudo()
        openaip_key = ICP.get_param('leulit_meteo.openaip_api_key', '')
        checkwx_key = ICP.get_param('leulit_meteo.checkwx_api_key', '')
        aemet_key = ICP.get_param('leulit_meteo.aemet_api_key', '')

        # 1. Coordenadas del OACI via OpenAIP
        airport_info = None
        lat = lon = None
        if openaip_key:
            airport_info = OpenAIPService.get_airport_by_icao(icao, openaip_key)
            if airport_info:
                lat = airport_info.get('lat')
                lon = airport_info.get('lon')

        # 2. ¿El propio OACI tiene METAR en CheckWX?
        ref_icao = None
        ref_nombre = None
        ref_dist_km = 0.0
        proveedor = 'aemet'
        tiene_metar = False
        station_info = None

        if checkwx_key:
            station_info = CheckWXService.get_station(icao, checkwx_key)
            if station_info:
                # Rellenar coordenadas si OpenAIP no las dio
                if lat is None:
                    lat = station_info.get('lat')
                    lon = station_info.get('lon')
                # Verificar si realmente tiene METAR
                test_metar = CheckWXService.get_metar(icao, checkwx_key)
                if test_metar:
                    tiene_metar = True
                    ref_icao = icao
                    ref_nombre = station_info.get('name', icao)
                    ref_dist_km = 0.0
                    country = station_info.get('country_code', '')
                    proveedor = 'aemet' if country == 'ES' else 'checkwx'

        # 3. Si no tiene METAR propio → buscar aeródromo con METAR cercano via CheckWX radius
        if not tiene_metar and lat is not None and checkwx_key:
            radius_nm = int(_SEARCH_RADIUS_KM / 1.852)
            candidates = CheckWXService.get_nearest_metar(lat, lon, radius_nm, checkwx_key)
            for candidate in candidates:
                cand_icao = candidate.get('icao', '')
                if not cand_icao or cand_icao == icao:
                    continue
                ref_icao = cand_icao
                ref_nombre = candidate.get('name') or cand_icao
                cand_lat = candidate.get('lat')
                cand_lon = candidate.get('lon')
                ref_dist_km = round(_haversine(lat, lon, cand_lat, cand_lon), 1) if cand_lat and cand_lon else 0.0
                country = candidate.get('country_code', '')
                proveedor = 'aemet' if country == 'ES' else 'checkwx'
                break

        # 4. FIR por heurística (el registro en tabla se gestiona en resolve())
        fir = _fir_heuristic(lat, lon)

        # 5. Estación AEMET más próxima (solo si tenemos coordenadas)
        station_code = None
        station_nombre_str = None
        station_dist = None
        if lat is not None and aemet_key:
            inventario = AemetOpenDataService.get_inventario_estaciones(aemet_key)
            if inventario:
                nearest, dist_km = AemetOpenDataService.find_nearest_station(
                    lat, lon, inventario)
                if nearest:
                    station_code = nearest.get('indicativo')
                    station_nombre_str = nearest.get('nombre')
                    station_dist = dist_km

        # 6. Determinar nombre del punto
        nombre = (airport_info.get('name') if airport_info else None) or \
                 (station_info.get('name') if station_info else None) or icao

        # 7. Crear registro
        vals = {
            'icao': icao,
            'nombre': nombre,
            'fir': fir,
            'tiene_metar_propio': tiene_metar,
            'ref_icao': ref_icao if not tiene_metar else None,
            'ref_nombre': ref_nombre if not tiene_metar else None,
            'ref_distancia_km': ref_dist_km if not tiene_metar else 0.0,
            'latitud': lat or 0.0,
            'longitud': lon or 0.0,
            'station_code': station_code,
            'station_nombre': station_nombre_str,
            'station_distancia_km': station_dist or 0.0,
            'proveedor_oficial': proveedor,
            'auto_resolved': True,
        }
        try:
            rec = self.sudo().with_context(no_recompute=True).create(vals)
            _logger.info(
                "leulit.meteo.icao.reference: auto-resuelto %s -> ref=%s fir=%s",
                icao, ref_icao or 'propio', fir)
            return rec
        except Exception as exc:
            # Concurrencia: otro hilo ya lo creó
            _logger.warning(
                "Auto-resolve %s: no se pudo crear registro (%s). "
                "Reintentando búsqueda.", icao, exc)
            return self.search([('icao', '=', icao)], limit=1) or None

    @api.model
    def _enrich_ref_icao(self, icao):
        """Busca el aeródromo MET más próximo y actualiza el registro cuando AEMET no tiene datos.

        Se llama desde el proveedor cuando AEMET no devuelve METAR/TAF para un OACI
        (registro existente pero marcado incorrectamente como tiene_metar_propio=True,
        o sin ref_icao configurado). Usa OpenAIP para coordenadas y CheckWX para
        encontrar el aeródromo con METAR oficial más cercano.

        Returns dict con ref_icao, ref_nombre, proveedor_oficial; o None si falla.
        """
        from .leulit_meteo_openaip_service import OpenAIPService
        from .leulit_meteo_checkwx_service import CheckWXService
        from .leulit_meteo_aemet_service import AemetOpenDataService

        ICP = self.env['ir.config_parameter'].sudo()
        openaip_key = ICP.get_param('leulit_meteo.openaip_api_key', '')
        checkwx_key = ICP.get_param('leulit_meteo.checkwx_api_key', '')
        aemet_key = ICP.get_param('leulit_meteo.aemet_api_key', '')

        rec = self.search([('icao', '=', icao)], limit=1)
        _logger.info(
            "_enrich_ref_icao %s: rec=%s openaip_key=%s checkwx_key=%s aemet_key=%s",
            icao, bool(rec), bool(openaip_key), bool(checkwx_key), bool(aemet_key))
        if not rec:
            return None

        lat = rec.latitud if rec.latitud else None
        lon = rec.longitud if rec.longitud else None
        _logger.info("_enrich_ref_icao %s: coords en registro → lat=%s lon=%s", icao, lat, lon)

        # Coordenadas: OpenAIP primero, CheckWX station como fallback
        if not lat and openaip_key:
            airport_info = OpenAIPService.get_airport_by_icao(icao, openaip_key)
            _logger.info("_enrich_ref_icao %s: OpenAIP → %s", icao, airport_info)
            if airport_info:
                lat = airport_info.get('lat')
                lon = airport_info.get('lon')

        if not lat and checkwx_key:
            station_info = CheckWXService.get_station(icao, checkwx_key)
            _logger.info("_enrich_ref_icao %s: CheckWX station → %s", icao, station_info)
            if station_info:
                lat = station_info.get('lat')
                lon = station_info.get('lon')

        if not lat:
            _logger.warning(
                "_enrich_ref_icao %s: no se obtuvieron coordenadas "
                "(openaip=%s, checkwx=%s)", icao, bool(openaip_key), bool(checkwx_key))
            return None

        # Buscar el aeródromo con METAR oficial más próximo
        ref_icao = None
        ref_nombre = None
        ref_dist_km = 0.0
        proveedor = 'aemet'

        if checkwx_key:
            radius_nm = int(_SEARCH_RADIUS_KM / 1.852)
            candidates = CheckWXService.get_nearest_metar(lat, lon, radius_nm, checkwx_key)
            _logger.info(
                "_enrich_ref_icao %s: CheckWX radius %dnm → %d candidatos",
                icao, radius_nm, len(candidates))
            for candidate in candidates:
                cand_icao = candidate.get('icao', '')
                if not cand_icao or cand_icao == icao:
                    continue
                ref_icao = cand_icao
                ref_nombre = candidate.get('name') or cand_icao
                cand_lat = candidate.get('lat')
                cand_lon = candidate.get('lon')
                if cand_lat and cand_lon:
                    ref_dist_km = round(_haversine(lat, lon, cand_lat, cand_lon), 1)
                country = candidate.get('country_code', '')
                proveedor = 'aemet' if country == 'ES' else 'checkwx'
                _logger.info(
                    "_enrich_ref_icao %s: ref encontrado → %s (%s, %.1f km)",
                    icao, ref_icao, proveedor, ref_dist_km)
                break
        else:
            _logger.warning(
                "_enrich_ref_icao %s: sin checkwx_key, no se puede buscar aeródromo próximo", icao)

        if not ref_icao:
            _logger.warning(
                "_enrich_ref_icao %s: no se encontró aeródromo MET en %d km",
                icao, _SEARCH_RADIUS_KM)
            return None

        # Estación AEMET más próxima (si no estaba ya configurada)
        station_code = rec.station_code or None
        station_nombre = rec.station_nombre or None
        station_dist = rec.station_distancia_km or None

        if not station_code and lat and aemet_key:
            inventario = AemetOpenDataService.get_inventario_estaciones(aemet_key)
            if inventario:
                nearest, dist_km = AemetOpenDataService.find_nearest_station(
                    lat, lon, inventario)
                if nearest:
                    station_code = nearest.get('indicativo')
                    station_nombre = nearest.get('nombre')
                    station_dist = dist_km

        # Actualizar el registro para que la próxima consulta sea directa
        try:
            rec.sudo().write({
                'tiene_metar_propio': False,
                'ref_icao': ref_icao,
                'ref_nombre': ref_nombre,
                'ref_distancia_km': ref_dist_km,
                'latitud': lat,
                'longitud': lon or 0.0,
                'proveedor_oficial': proveedor,
                'station_code': station_code,
                'station_nombre': station_nombre,
                'station_distancia_km': station_dist or 0.0,
            })
            _logger.info(
                "_enrich_ref_icao: %s → ref=%s (%.1f km, proveedor=%s)",
                icao, ref_icao, ref_dist_km, proveedor)
        except Exception as exc:
            _logger.warning("_enrich_ref_icao %s: error al actualizar: %s", icao, exc)
            return None

        return {
            'ref_icao': ref_icao,
            'ref_nombre': ref_nombre,
            'ref_distancia_km': ref_dist_km,
            'proveedor_oficial': proveedor,
        }
