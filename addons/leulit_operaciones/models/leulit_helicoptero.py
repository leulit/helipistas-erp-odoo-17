#-*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class leulit_helicoptero(models.Model):
    _name = "leulit.helicoptero"
    _inherit = "leulit.helicoptero"


    # @api.depends('airtime','ovhoras')
    # def _calc_ov_afterhoras(self):
    #     for item in self:
    #         item.ov_afterhoras = item.airtime - item.ovhoras


    # @api.depends('doitov','tareaov')
    # def _calc_ovrh_first(self):
    #     horas = 0.0
    #     for item in self:
    #         if item.doitov != True:
    #             if item.tareaov:
    #                 horas = float(item.tareaov.horas_vuelo) - item.airtime
    #         item.ovrh_first = horas

    
    # @api.depends('doitov','tareaov','fechafab')
    # def _calc_ovrd_first(self):
    #     dias = 0
    #     for item in self:
    #         if item.doitov != True:
    #             if item.tareaov and item.fechafab:
    #                 fecha1 = datetime.strptime( item.fechafab, "%Y-%m-%d" )
    #                 adddias = item.tareaov.calendario_dias
    #                 fecha2 = fecha1 + timedelta(days=adddias)
    #                 hoy = datetime.now()
    #                 dias = (fecha2 - hoy).days
    #         item.ovrd_first = dias


    def _get_sling_cycles(self):
        for item in self:
            valor = 0
            for vuelo in self.env['leulit.vuelo'].search([('estado','=','cerrado'),('helicoptero_id','=',item.id),('sling_cycle','>',0)]):
                valor += vuelo.sling_cycle
            item.sling_cycles = valor


    @api.depends('arlandingstart')
    def _calc_arlandings_helicoptero(self):
        for item in self:
            vuelos = self.env['leulit.vuelo'].search([('helicoptero_id', '=', item.id)])
            landings = 0
            for vuelo in vuelos:
                landings += vuelo.arlanding
            item.arlandings = landings + item.arlandingstart



    vuelo_ids = fields.One2many(comodel_name='leulit.vuelo', inverse_name='helicoptero_id', string='Vuelos', domain=[('estado','=','cerrado')])
    # tareaov = fields.Many2one('leulit.programa_mantenimiento_tarea', 'Tarea Overhaul')
    # ovfecha = fields.Date(related='tareaov.last_done_date',string='Fecha último overhaul')
    # ovhoras = fields.Float(related='tareaov.last_done_hours',string='Horas último overhaul')
    # ov_afterhoras = fields.Float(compute='_calc_ov_afterhoras',string='Time Since Overhaul (TSO)',store=False)
    # ovrh_first = fields.Float(compute='_calc_ovrh_first',string='Remaining (H)',store=False)
    # ovrd_first = fields.Float(compute='_calc_ovrd_first',string='Remaining (DY)',store=False)
    # ov_rh = fields.Integer(related='tareaov.remainder_hours',string='Remaining (H)')
    # ov_rd = fields.Integer(related='tareaov.remainder_days',string='Remaining (DY)')
    # ov_sh = fields.Char(related='tareaov.semaforo_hours',string='')
    # ov_sdy = fields.Char(related='tareaov.semaforo_days',string='')

    # remhorasmotor = fields.Float(related='rotable_motor.potencialremahoras',string='Remaining (H)')
    # remdymotor = fields.Integer(related='rotable_motor.potencialremadias',string='Remaining (DY)')
    sling_cycles = fields.Integer(compute='_get_sling_cycles',string='Ciclos de Eslinga')
    arlandingstart = fields.Integer('Autorotation Landings inicio', required=True)
    arlandings = fields.Integer(compute='_calc_arlandings_helicoptero', string='Total Autorotation Landings', store=False)

    