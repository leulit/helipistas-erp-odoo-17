# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, date
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"
    

    @api.onchange('parent_id')
    def onchange_parent(self):
        if self._origin:
            if self._origin.parent_id != False:
                raise UserError('No se puede cambiar el equipamiento padre.')
            

    def write(self, vals):
        if 'production_lot' in vals:
            pieza_antigua = False
            if self.production_lot:
                pieza_antigua = self.production_lot
            result = super(MaintenanceEquipment, self).write(vals)
            values_equipment_changes = {
                'equipment_id' : self.id,
                'old_production_lot_id' : pieza_antigua.id if pieza_antigua else False,
                'new_production_lot_id' : self.production_lot.id,
                'tsn_inicio' : self.production_lot.tsn_actual if self.production_lot.tsn_actual > 0 and self.production_lot.tsn_actual != self.production_lot.tsn_inicio else self.production_lot.tsn_inicio,
                'tso_inicio' : self.production_lot.tso_actual if self.production_lot.tso_actual > 0 and self.production_lot.tso_actual != self.production_lot.tso_inicio else self.production_lot.tso_inicio,
                'ng_inicio' : self.production_lot.ng_actual if self.production_lot.ng_actual > 0 and self.production_lot.ng_actual != self.production_lot.ng_inicio else self.production_lot.ng_inicio,
                'nf_inicio' : self.production_lot.nf_actual if self.production_lot.nf_actual > 0 and self.production_lot.nf_actual != self.production_lot.nf_inicio else self.production_lot.nf_inicio,
                'date' : self.effective_date
            }
            self.env['maintenance.equipment.changes'].create(values_equipment_changes)
        else:
            result = super(MaintenanceEquipment, self).write(vals)
        return result


    @api.depends('category_id')
    def is_historico(self):
        for item in self:
            item.is_historico_pieza = False
            if item.category_id:
                if item.category_id.name == 'Pieza':
                    item.is_historico_pieza = True


    def get_last_change(self):
        return self.env['maintenance.equipment.changes'].search([('equipment_id','=',self.id)],order='date desc',limit=1)


    historico_pieza = fields.One2many(comodel_name='maintenance.equipment.changes', inverse_name='equipment_id', string='Histórico')
    is_historico_pieza = fields.Boolean(compute='is_historico',string='Is histórico pieza?',store=False)
