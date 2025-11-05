
from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class MaintenancePlan(models.Model):
    _inherit = "maintenance.plan"


    @api.depends('equipment_id')
    def _get_componentes_from_equipment(self):
        for item in self:
            lots = []
            if item.equipment_id:
                _logger.error("Equipment ID: %s", item.equipment_id.id)
                for child in item.equipment_id.get_all_childs():
                    _logger.error("Child Equipment ID: %s", child.id)
                    if child.production_lot:
                        _logger.error("Adding Production Lot ID: %s", child.production_lot.id)
                        lots.append(child.production_lot.id)
            item.componentes = [(6, 0, lots)]

    
    componentes = fields.Many2many(compute=_get_componentes_from_equipment, comodel_name="stock.lot", string="Componentes")