# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
import pyqrcode

_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _name = 'stock.lot'
    _inherit = 'stock.lot'


    @api.depends('rel_form_one_ids')
    def _get_form_one(self):
        for item in self:
            ids = []
            for rel in item.rel_form_one_ids:
                ids.append(rel.form_one.id)
            if not ids:
                ids = False
            item.form_one_ids = ids

    @api.depends('tsn_inicio')
    def _get_tsn(self):
        for item in self:
            item.tsn_actual = 0
            last_change = self.env['maintenance.equipment.changes'].search([('new_production_lot_id','=',item.id)], order='date desc', limit=1)
            if last_change:
                item.tsn_actual = last_change.tsn_actual
            else:
                item.tsn_actual = item.tsn_inicio

    @api.depends('tso_inicio')
    def _get_tso(self):
        for item in self:
            item.tso_actual = 0
            last_change = self.env['maintenance.equipment.changes'].search([('new_production_lot_id','=',item.id)], order='date desc', limit=1)
            if last_change:
                item.tso_actual = last_change.tso_actual
            else:
                item.tso_actual = item.tso_inicio

    @api.depends('ng_inicio')
    def _get_ng(self):
        for item in self:
            item.ng_actual = 0
            last_change = self.env['maintenance.equipment.changes'].search([('new_production_lot_id','=',item.id)], order='date desc', limit=1)
            if last_change:
                item.ng_actual = last_change.ng_actual
            else:
                item.ng_actual = item.ng_inicio

    @api.depends('nf_inicio')
    def _get_nf(self):
        for item in self:
            item.nf_actual = 0
            last_change = self.env['maintenance.equipment.changes'].search([('new_production_lot_id','=',item.id)], order='date desc', limit=1)
            if last_change:
                item.nf_actual = last_change.nf_actual
            else:
                item.nf_actual = item.nf_inicio

    sn = fields.Char(string="Serial Number", default="N/A")
    rel_form_one_ids = fields.One2many(comodel_name="leulit.rel_formone_lot", inverse_name="pieza_id", string="")
    form_one_ids = fields.One2many(compute=_get_form_one, comodel_name="leulit.maintenance_form_one", string="Form One")
    task_ids = fields.One2many(comodel_name="project.task", inverse_name="production_lot_id", string="Tareas")
    is_motor = fields.Boolean(related="product_id.is_motor", string="Motor")
    tipo_motor = fields.Selection(related="product_id.tipo_motor", selection=[('piston', 'Pistón'),('turbina', 'Turbina')], string="Tipo motor")
    tsn = fields.Float(string="TSN")
    tso = fields.Float(string="TSO")
    nf = fields.Float(string="NF")
    ng = fields.Float(string="NG")
    date_last_overhaul = fields.Date(string="Fecha overhaul")
    tsn_inicio = fields.Float(string="TSN Inicio")
    tsn_actual = fields.Float(compute=_get_tsn, string="TSN")
    tso_inicio = fields.Float(string="TSO Inicio")
    tso_actual = fields.Float(compute=_get_tso, string="TSO")
    ng_inicio = fields.Float(string="NG Inicio")
    ng_actual = fields.Float(compute=_get_ng, string="NG")
    nf_inicio = fields.Float(string="NF Inicio")
    nf_actual = fields.Float(compute=_get_nf, string="NF")


    def open_trabajos_realizados(self):
        action_id = self.env.ref('leulit_taller.leulit_20231024_1458_action').read()[0]
        if self.task_ids:
            action_id['domain'] = [('id', 'in', self.task_ids.ids)]
        else:
            action_id['domain'] = [('id', '=', '0')]
        return action_id