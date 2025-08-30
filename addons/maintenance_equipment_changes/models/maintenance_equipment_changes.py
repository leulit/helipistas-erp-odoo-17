# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

from datetime import date, datetime, timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class MaintenanceEquipmentChanges(models.Model):
    _name = 'maintenance.equipment.changes'
    _description = 'Maintenance Equipment Changes'
    _order = "date desc, id asc"

    @api.depends('equipment_id','tsn_inicio')
    def _get_tsn(self):
        for item in self:
            item.tsn_actual = 0.0
            if item.equipment_id:
                if item.equipment_id.first_parent:
                    if item.equipment_id.first_parent.helicoptero:
                        now = datetime.now()
                        next_change = self.search([('equipment_id','=',item.equipment_id.id),('date','>',item.date)], order='date asc', limit=1)
                        datos = self.env['leulit.vuelo'].acumulados_between_dates(item.equipment_id.first_parent.helicoptero.id, item.date.date(), now.date() if not next_change else next_change.date.date())
                        airtime = 0.0
                        if datos:
                            airtime = datos[0][0]
                        item.tsn_actual = item.tsn_inicio + airtime
            else:
                item.tsn_actual = item.tsn_inicio
    
    @api.depends('equipment_id','tso_inicio')
    def _get_tso(self):
        for item in self:
            item.tso_actual = 0.0
            if item.equipment_id:
                if item.equipment_id.first_parent:
                    if item.equipment_id.first_parent.helicoptero:
                        now = datetime.now()
                        next_change = self.search([('equipment_id','=',item.equipment_id.id),('date','>',item.date)], order='date asc', limit=1)
                        datos = self.env['leulit.vuelo'].acumulados_between_dates(item.equipment_id.first_parent.helicoptero.id, item.date.date(), now.date() if not next_change else next_change.date.date())
                        airtime = 0.0
                        if datos:
                            airtime = datos[0][0]
                        item.tso_actual = item.tso_inicio + airtime
            else:
                item.tso_actual = item.tso_inicio
    
    @api.depends('equipment_id','ng_inicio')
    def _get_ng(self):
        for item in self:
            item.ng_actual = 0.0
            if item.equipment_id:
                if item.equipment_id.first_parent:
                    if item.equipment_id.first_parent.helicoptero:
                        now = datetime.now()
                        next_change = self.search([('equipment_id','=',item.equipment_id.id),('date','>',item.date)], order='date asc', limit=1)
                        datos = self.env['leulit.vuelo'].acumulados_between_dates(item.equipment_id.first_parent.helicoptero.id, item.date.date(), now.date() if not next_change else next_change.date.date())
                        ng_acumulados = 0.0
                        if datos:
                            ng_acumulados = datos[0][1]
                        item.ng_actual = item.ng_inicio + ng_acumulados
            else:
                item.ng_actual = item.ng_inicio
    
    @api.depends('equipment_id','nf_inicio')
    def _get_nf(self):
        for item in self:
            item.nf_actual = 0.0
            if item.equipment_id:
                if item.equipment_id.first_parent:
                    if item.equipment_id.first_parent.helicoptero:
                        now = datetime.now()
                        next_change = self.search([('equipment_id','=',item.equipment_id.id),('date','>',item.date)], order='date asc', limit=1)
                        datos = self.env['leulit.vuelo'].acumulados_between_dates(item.equipment_id.first_parent.helicoptero.id, item.date.date(), now.date() if not next_change else next_change.date.date())
                        nf_acumulados = 0.0
                        if datos:
                            nf_acumulados = datos[0][1]
                        item.nf_actual = item.nf_inicio + nf_acumulados
            else:
                item.nf_actual = item.nf_inicio
    

    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipo', required=True)
    old_production_lot_id = fields.Many2one(comodel_name='stock.production.lot', string='Pieza anterior')
    new_production_lot_id = fields.Many2one(comodel_name='stock.production.lot', string='Pieza nueva')
    date = fields.Datetime(string='Fecha', required=True)
    tsn_inicio = fields.Float(string='TSN Inicio')
    tso_inicio = fields.Float(string='TSO Inicio')
    ng_inicio = fields.Float(string='NG Inicio')
    nf_inicio = fields.Float(string='NF Inicio')
    tsn_actual = fields.Float(compute=_get_tsn, string='TSN Actual')
    tso_actual = fields.Float(compute=_get_tso, string='TSO Actual')
    ng_actual = fields.Float(compute=_get_ng, string='NG Actual')
    nf_actual = fields.Float(compute=_get_nf, string='NF Actual')