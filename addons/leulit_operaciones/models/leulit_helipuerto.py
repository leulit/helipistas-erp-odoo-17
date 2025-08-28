# -*- encoding: utf-8 -*-

import pytz

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
    _inherit        = ['mail.thread']

    @api.model
    def create(self, vals):
        if vals['lat'] == 0:
            raise UserError('Error!! Latitud con valor 0')
        if vals['long'] == 0:
            raise UserError('Error!! Longitud con valor 0')
        if vals['elevacion'] == 0:
            raise UserError('Error!! Elevación con valor 0')
        return super(leulit_helipuerto, self).create(vals)  


    @api.depends('name', 'descripcion')
    def name_get(self):
        res = []
        for item in self:
            res.append((item.id, '(%s) %s' % (item.name, item.descripcion)))
        return res
    
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
        

    name = fields.Char('Indicativo',size=40, required=True)
    descripcion = fields.Char('Nombre', size=255, required=True)
    municipio = fields.Char('Ciudad/Provincia',size=40, required=True)
    direccion = fields.Text('Dirección', required=True)
    telefono = fields.Char('Teléfono',size=40, required=True)
    hayjeta1 = fields.Boolean('Combustible JET A1')
    hayavgas = fields.Boolean('Combustible AVGAS')
    latitud = fields.Char('Latitud',size=20)
    longitud = fields.Char('Longitud',size=20)
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

        view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones','leulit_20201026_1156_form')
        view_id = view_ref and view_ref[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Punto',
            'res_model': 'leulit.ruta_punto',
            'view_mode': 'form',
            'view_id': view_id,
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
