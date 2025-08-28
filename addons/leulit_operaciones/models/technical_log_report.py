# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64

_logger = logging.getLogger(__name__)


class leulit_technical_log_report(models.Model):
    _name           = "leulit.technical_log_report"
    _description    = "leulit_technical_log_report"

    def _get_vuelos_by_fecha(self):
        for item in self:
            self.vuelos = self.env['leulit.vuelo'].search([('helicoptero_id','=',item.helicoptero_id.id),('estado','in',['postvuelo','cerrado']),('fechavuelo','=',item.fecha)], limit=None, order='fechasalida asc')

    def _get_before_tservicio(self):
        res = {}
        for item in self:
            diaant = utilitylib.addDays(item.fecha, -1)
            heliid = item.helicoptero_id.id
            datos = self.env['leulit.vuelo'].acumulados_in_date(heliid, diaant)
            self.before_tservicio = datos['suma_tiemposervicio']

    def _get_before_airtime(self):
        for item in self:
            diaant = utilitylib.addDays(item.fecha, -1)
            heliid = item.helicoptero_id.id
            datos = self.env['leulit.vuelo'].acumulados_in_date(heliid, diaant)
            self.before_airtime = datos['suma_airtime']


    def _get_before_nf(self):
        nf = 0.0
        for item in self:
            diaant = utilitylib.addDays(item.fecha, -1)
            datos = self.env['leulit.vuelo'].acumulados_motor_in_date(item.helicoptero_id.id, diaant)
            nf = datos['suma_nf']
            self.before_nf = nf
    
    def _get_before_ng(self):
        ng = 0.0
        #for item in self.browse(cr, uid, ids, context):
        for item in self:
            diaant = utilitylib.addDays(item.fecha, -1)
            datos = self.env['leulit.vuelo'].acumulados_motor_in_date(item.helicoptero_id.id, diaant)
            ng = datos['suma_ng']
            self.before_ng = ng
    
    def _get_vuelos_airtime(self):
        res = {}
        #for item in self.browse(cr, uid, ids, context):
        for item in self:
            datos = self.env['leulit.vuelo'].acumulados_motor_in_date(item.helicoptero_id.id, item.fecha)
            self.vuelos_airtime = datos['suma_airtime']
        return res
    
    def _get_vuelos_nf(self):
        res = {}
        nf = 0.0
        for item in self:
            datos = self.env['leulit.vuelo'].acumulados_motor_in_date(item.helicoptero_id.id, item.fecha)
            nf = datos['suma_nf']
            self.vuelos_nf = nf
    
    def _get_vuelos_ng(self):
        res = {}
        ng = 0.0
        for item in self:
            datos = self.pool['leulit.vuelo'].acumulados_motor_in_date(item.helicoptero_id.id, item.fecha)
            ng = datos['suma_ng']
            self.vuelos_ng = ng


    vuelos = fields.One2many(compute=_get_vuelos_by_fecha, comodel_name='leulit.vuelo', string='Vuelos', store=False)
    fecha = fields.Date('Fecha')
    helicoptero_id = fields.Many2one(comodel_name='leulit.helicoptero', string='Helicóptero', required=True)
    before_aritime = fields.Float(compute=_get_before_airtime, string='Airtime Before', store=False)
    before_tservicio = fields.Float(compute=_get_before_tservicio, string='T. servicio Before', store=False)
    before_nf = fields.Float(compute=_get_before_nf, string='NF Before', store=False)
    before_ng = fields.Float(compute=_get_before_ng, string='NG Before', store=False)
    vuelos_airtime = fields.Float(compute=_get_vuelos_airtime, string='Airtime Vuelos', store=False)
    vuelos_nf = fields.Float(compute=_get_vuelos_nf, string='NF Vuelos', store=False)
    vuelos_ng = fields.Float(compute=_get_vuelos_ng, string='NG Vuelos', store=False)
