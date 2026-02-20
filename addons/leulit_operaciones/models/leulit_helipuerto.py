# -*- encoding: utf-8 -*-

import base64
import html as py_html
import io
import pytz
import zipfile

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs
    
class leulit_helipuerto(models.Model):
    _name             = "leulit.helipuerto"
    _description    = "leulit_helipuerto"
    _inherit        = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "display_name"

    @api.model
    def create(self, vals):
        if vals.get('lat') == 0:
            raise UserError('Error!! Latitud con valor 0')
        if vals.get('long') == 0:
            raise UserError('Error!! Longitud con valor 0')
        if vals.get('elevacion') == 0:
            raise UserError('Error!! Elevación con valor 0')
        return super(leulit_helipuerto, self).create(vals)  

    display_name = fields.Char(string="Display Name", compute='_compute_display_name', store=True)

    @api.depends('name', 'descripcion')
    def _compute_display_name(self):
        """
        Odoo 17: Reemplaza name_get() con _compute_display_name()
        """
        for item in self:
            if item.name and item.descripcion:
                item.display_name = '(%s) %s' % (item.name, item.descripcion)
            elif item.name:
                item.display_name = item.name
            else:
                item.display_name = 'Helipuerto'
    
    def getTipoOperacion(self):
        return utilitylib.leulit_getTipoOperacion()

    def _get_horario(self):
        return (
            ('HJ', 'HJ'),
            ('H24', 'H24'),
            ('otros', 'Otros'),
        )

    def _get_attachments(self):
        for item in self:
            attachment_ids = self.env['ir.attachment'].search([('res_model','=','leulit.helipuerto'),('res_id','=',item.id)])
            item.attachment_ids  = attachment_ids

    @api.depends('puntos_ids')
    def _get_punto_generado(self):
        for item in self:
            item.punto_generado = False
            if len(item.puntos_ids.ids) > 0:
                item.punto_generado = True
        

    name = fields.Char('Indicativo', required=True)
    descripcion = fields.Char('Nombre',  required=True)
    municipio = fields.Char('Ciudad/Provincia', required=True)
    direccion = fields.Text('Dirección', required=True)
    telefono = fields.Char('Teléfono', required=True)
    hayjeta1 = fields.Boolean('Combustible JET A1')
    hayavgas = fields.Boolean('Combustible AVGAS')
    latitud = fields.Char('Latitud',)
    longitud = fields.Char('Longitud',)
    lat = fields.Float('Latitud (Grados Decimales)', required=True, digits=(10,8))
    long = fields.Float('Longitud (Grados Decimales)', required=True, digits=(10,8))
    elevrumbo = fields.Char('Elevación - Rumbo')
    superficie = fields.Selection([('grava','Grava'),('cesped','Césped'),('asfalto','Asfalto')], string='Superficie',required=True)
    distancia = fields.Char('Dimensiones FATO', required=True)
    tlof = fields.Char('Dimensiones TLOF', required=True)
    twr = fields.Char('TWR')
    twrcerca = fields.Char('TWR más próxima (MHz)')
    balizaje = fields.Char('Luces de balizaje', required=True)
    viento = fields.Char('Viento', required=True)
    observaciones = fields.Text('Observaciones')
    tipooperacion = fields.Selection(getTipoOperacion, string='Tipo operación')
    dificultad = fields.Selection([('a', 'A (Aproximación por instrumentos 3D)'),('b', 'B'),('c', 'C (Requiere visita al Aeródromo)')], 'Categoría', required=True)
    operaciones_AOCP3 = fields.Boolean('Operaciones AOCP3')
    operaciones_AOCEH05 = fields.Boolean('Operaciones AOCEH05')
    operaciones_ATO = fields.Boolean('Operaciones ATO')
    operaciones_TTAA = fields.Boolean('Operaciones TTAA')
    operaciones_LCI = fields.Boolean('Operaciones LCI')
    vuelo_id = fields.Many2one('leulit.vuelo', 'Vuelo', ondelete='set null')
    attachment_ids = fields.One2many(compute='_get_attachments',comodel_name='ir.attachment',string='Ficheros',store=False)
    tz = fields.Selection(_tz_get, string='Zona horaria', default=lambda self: self._context.get('tz'))
    horario_operacion = fields.Selection(_get_horario, string='Horario Operación', required=True)
    horario_combustible = fields.Selection(_get_horario, string='Horario Combustible', required=True)
    asistencia_tierra = fields.Text(string='Asistencia en tierra', required=True)
    elevacion = fields.Integer(string='Elevación (Ft)', required=True)
    rumbo_aproximacion = fields.Char(string='Rumbo aproximación', required=True)
    rumbo_salida = fields.Char(string='Rumbo salida', required=True)
    calle_rodaje = fields.Text(string='Calle de rodaje', default='N/A', required=True)
    minimos_meteo = fields.Selection([('a','Espacio aéreo A, B, C, D, E: 800 m de visibilidad horizontal. 600 pies de techo. Libre de nubes y con la superficie a la vista.'),('b','Espacio aéreo F, G : 5 km de visibilidad horizontal. 1.500 metros horizontalmente y 300 metros (1000 ft) verticalmente.')], string='Mínimos meteorología', required=True)
    operaciones_performance = fields.Many2many('leulit.operaciones_performance','leulit_helipuerto_op_perf_rel', 'helipuerto_id', 'op_perf_id', string='Operaciones/Performance', required=True)
    procedimiento_llegadas_salidas = fields.Text(string='Procedimiento de llegadas y salidas', required=True)
    procedimiento_activacion = fields.Text(string='Procedimiento de activacion')
    freq_aerodromo = fields.Char(string='Frecuencia aeródromo (MHz)', required=True)
    obstaculos_area_movimiento = fields.Text(string='Obstáculos y área de movimiento', required=True)
    procedimiento_des_embarque_pasajeros = fields.Text(string='Procedimiento', required=True)
    img_1 = fields.Image('Imagen 1', required=True)
    img_2 = fields.Image('Imagen 2')
    img_3 = fields.Image('Imagen 3')
    img_4 = fields.Image('Imagen 4')
    edicion_revision = fields.Char('Edición y revisión', required=True)
    puntos_ids = fields.One2many(comodel_name="leulit.ruta_punto", inverse_name="helipuerto_id", string="Puntos")
    punto_generado = fields.Boolean(compute=_get_punto_generado, string="¿Punto generado?")



    def generar_punto(self):
        punto = self.env['leulit.ruta_punto'].create({
            'indicativo' : self.name,
            'descripcion' : self.descripcion,
            'latitud' : self.lat,
            'longitud' : self.long,
            'altitud' : self.elevacion,
            'helipuerto_id' : self.id
        })

        self.ensure_one()
        view = self.env.ref('leulit_operaciones.leulit_20201026_1156_form',raise_if_not_found=False)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Punto',
            'res_model': 'leulit.ruta_punto',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'res_id': punto.id,
            'target': 'new',
        }


    def generar_ficha_helipuerto_aerodromo(self):
        try:
            op_perf_list = ''
            index = 0
            for op_perf in self.operaciones_performance:
                if index == 0:
                    op_perf_list += '%s' % (op_perf.name)
                else:
                    op_perf_list += ' ,%s' % (op_perf.name)
                index += 1
            categ = 'N/A'
            if self.dificultad == 'a': 
                categ = 'A'
            if self.dificultad == 'b': 
                categ = 'B'
            if self.dificultad == 'c': 
                categ = 'C'
            minimos_meteo = 'N/A'
            if self.minimos_meteo == 'a': 
                minimos_meteo = 'Espacio aéreo A, B, C, D, E: 800 m de visibilidad horizontal. 600 pies de techo. Libre de nubes y con la superficie a la vista.'
            if self.minimos_meteo == 'b': 
                minimos_meteo = 'Espacio aéreo F, G : 5 km de visibilidad horizontal. 1.500 metros horizontalmente y 300 metros (1000 ft) verticalmente.'
            combus = ''
            if self.hayavgas:
                combus += 'AVGAS '
            if self.hayjeta1:
                if combus:
                    combus += ', JETA1'
                else:
                    combus += 'JETA1'
            if combus == '':
                combus = 'N/A'
            company_helipistas = self.env['res.company'].search([('name','like','Helipistas')])
            data = {
                'logo_hlp' : company_helipistas.logo_reports if company_helipistas else False,
                'nombre':'%s (%s)' % (self.descripcion, self.name),
                'latitud': self.lat,
                'longitud': self.long,
                'elevacion': self.elevacion,
                'direccion': '%s, %s' % (self.direccion, self.municipio),
                'telefono': self.telefono,
                'combus': combus,
                'asistencia_tierra': self.asistencia_tierra,
                'h_operacion': self.horario_operacion,
                'h_combus': self.horario_combustible,
                'rumbo_aprox': self.rumbo_aproximacion,
                'rumbo_salida': self.rumbo_salida,
                'fato': self.distancia,
                'tlof': self.tlof,
                'rodaje': self.calle_rodaje,
                'viento': self.viento,
                'luces': self.balizaje,
                'minimos_meteo': minimos_meteo,
                'categoria': categ,
                'operaciones_performance': op_perf_list,
                'procedimiento_des_embarque_pasajeros': self.procedimiento_des_embarque_pasajeros,
                'procedimiento_llegadas_salidas': self.procedimiento_llegadas_salidas,
                'procedimiento_activacion': self.procedimiento_activacion if self.procedimiento_activacion else 'N/A',
                'obstaculos': self.obstaculos_area_movimiento,
                'frec_aerodromo': self.freq_aerodromo,
                'frec_cercana': self.twrcerca if self.twrcerca else 'N/A',
                'img_1': self.img_1,
                'img_2': self.img_2,
                'img_3': self.img_3,
                'img_4': self.img_4,
                'edicion_revision': self.edicion_revision,
            }
            return self.env.ref('leulit_operaciones.ficha_helipuerto_report').report_action([],data=data)
        except Exception as e:
            raise UserError ('Faltan datos en el helipuerto/aeródromo, revisar antes de seguir.')

    def _format_helipuerto_field_value(self, field_name, field_def):
        self.ensure_one()
        value = self[field_name]

        if field_def.type == 'boolean':
            return 'Sí' if value else 'No'
        if field_def.type == 'many2one':
            return value.display_name if value else ''
        if field_def.type in ('many2many', 'one2many'):
            return ', '.join(value.mapped('display_name')) if value else ''
        if field_def.type == 'selection':
            selection = field_def.selection(self) if callable(field_def.selection) else field_def.selection
            return dict(selection).get(value, value or '')
        if field_def.type == 'date':
            return fields.Date.to_string(value) if value else ''
        if field_def.type == 'datetime':
            return fields.Datetime.to_string(value) if value else ''

        return '' if value in (False, None) else str(value)

    def _build_helipuerto_kml_description(self):
        self.ensure_one()

        excluded_fields = {
            'id',
            'display_name',
            '__last_update',
            'message_ids',
            'message_follower_ids',
            'message_partner_ids',
            'message_main_attachment_id',
            'activity_ids',
            'activity_state',
            'activity_user_id',
            'activity_type_id',
            'activity_date_deadline',
            'activity_summary',
            'activity_exception_icon',
            'activity_exception_decoration',
            'activity_calendar_event_id',
            'website_message_ids',
            'message_has_error',
            'message_has_error_counter',
            'message_needaction',
            'message_needaction_counter',
            'message_attachment_count',
            'message_bounce',
            'is_follower',
            'has_message',
            'message_is_follower',
            'message_unread',
            'message_unread_counter',
            'message_type',
            'message_channel_ids',
            'message_has_sms_error',
            'message_has_sms_error_counter',
            'activity_exception_icon',
        }

        image_links = []
        rows = []
        key_field_names = {
            'name',
            'descripcion',
            'edicion_revision',
            'municipio',
            'direccion',
            'telefono',
            'lat',
            'long',
            'elevacion',
            'superficie',
            'horario_operacion',
            'horario_combustible',
        }
        key_rows = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')

        for field_name, field_def in self._fields.items():
            if field_name in excluded_fields:
                continue
            if field_def.type == 'binary':
                image_b64 = self[field_name]
                if image_b64:
                    image_links.append({
                        'label': field_def.string,
                        'url': '%s/web/image/leulit.helipuerto/%s/%s' % (base_url, self.id, field_name),
                    })
                continue

            value = self._format_helipuerto_field_value(field_name, field_def)
            if value:
                row_data = {
                    'label': field_def.string,
                    'value': value,
                }
                rows.append(row_data)
                if field_name in key_field_names:
                    key_rows.append(row_data)

        title = py_html.escape(self.descripcion or self.name or 'Helipuerto/Aeródromo')
        subtitle = py_html.escape(self.name or '')
        revision = py_html.escape(self.edicion_revision or 'N/A')
        descripcion = py_html.escape(self.descripcion or 'Sin descripción')

        operaciones_badges = []
        if self.operaciones_AOCP3:
            operaciones_badges.append('AOCP3')
        if self.operaciones_AOCEH05:
            operaciones_badges.append('AOCEH05')
        if self.operaciones_ATO:
            operaciones_badges.append('ATO')
        if self.operaciones_TTAA:
            operaciones_badges.append('TTAA')
        if self.operaciones_LCI:
            operaciones_badges.append('LCI')

        badges_html = ', '.join([py_html.escape(badge) for badge in operaciones_badges]) or 'Sin operación marcada'

        def _rows_to_html(data_rows):
            return ''.join([
                '<tr><th>%s</th><td>%s</td></tr>' % (
                    py_html.escape(row['label']),
                    py_html.escape(row['value']).replace('\n', '<br/>'),
                )
                for row in data_rows
            ])

        key_rows_html = _rows_to_html(key_rows)
        rows_html = _rows_to_html(rows)

        image_html = ''.join([
            '<li><a href="%s" target="_blank">%s</a></li>' % (
                py_html.escape(image['url']),
                py_html.escape(image['label']),
            )
            for image in image_links
        ]) or '<li>Sin imágenes</li>'

        return (
            '<div style="font-family:Arial,sans-serif; min-width:420px;">'
            '<div style="background:#1f2a44;color:#fff;padding:10px 12px;border-radius:8px;">'
            '<div style="font-size:18px;font-weight:700;">%s</div>'
            '<div style="font-size:14px;opacity:0.95;">%s</div>'
            '<div style="margin-top:4px;font-size:12px;">Edición/Revisión: %s</div>'
            '<div style="margin-top:8px;font-size:12px;line-height:1.4;">%s</div>'
            '</div>'
            '<div style="margin:10px 0 6px;font-size:13px;font-weight:700;color:#1f2a44;">Operaciones</div>'
            '<div style="font-size:12px;">%s</div>'
            '<div style="margin:10px 0 6px;font-size:13px;font-weight:700;color:#1f2a44;">Datos clave</div>'
            '<table style="width:100%%;border-collapse:collapse;background:#fff;border:1px solid #d8dde6;">%s</table>'
            '<div style="margin:10px 0 6px;font-size:13px;font-weight:700;color:#1f2a44;">Imágenes (URL)</div>'
            '<ul>%s</ul>'
            '<div style="margin:10px 0 6px;font-size:13px;font-weight:700;color:#1f2a44;">Ficha completa</div>'
            '<table style="width:100%%;border-collapse:collapse;background:#fff;border:1px solid #d8dde6;">%s</table>'
            '</div>'
        ) % (
            title,
            subtitle,
            revision,
            descripcion,
            badges_html,
            key_rows_html,
            image_html,
            rows_html,
        )

    def action_exportar_mapa_kmz(self):
        if not self:
            raise UserError(_('Debes seleccionar al menos un helipuerto/aeródromo.'))

        placemarks = []

        for record in self:
            if record.lat is False or record.long is False:
                continue

            lat = float(record.lat)
            lng = float(record.long)

            name = py_html.escape(record.display_name or record.name or 'Helipuerto/Aeródromo')
            description_html = record._build_helipuerto_kml_description()
            placemarks.append(
                '<Placemark>'
                '<name>%s</name>'
                '<description><![CDATA[%s]]></description>'
                '<Point><coordinates>%s,%s,0</coordinates></Point>'
                '</Placemark>' % (name, description_html, lng, lat)
            )

        if not placemarks:
            raise UserError(_('Ninguno de los registros seleccionados tiene latitud/longitud válidas.'))

        kml_content = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<kml xmlns="http://www.opengis.net/kml/2.2">'
            '<Document>'
            '<name>Helipuertos/Aeródromos seleccionados</name>'
            '<description>Exportación de helipuertos con descripción completa e imágenes por URL</description>'
            '%s'
            '</Document>'
            '</kml>'
        ) % ''.join(placemarks)

        kmz_buffer = io.BytesIO()
        with zipfile.ZipFile(kmz_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as kmz_file:
            kmz_file.writestr('doc.kml', kml_content.encode('utf-8'))

        file_name = 'helipuertos_mapa_%s.kmz' % fields.Datetime.now().strftime('%Y%m%d_%H%M%S')
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(kmz_buffer.getvalue()),
            'mimetype': 'application/vnd.google-earth.kmz',
            'res_model': 'leulit.helipuerto',
            'res_id': self[0].id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
