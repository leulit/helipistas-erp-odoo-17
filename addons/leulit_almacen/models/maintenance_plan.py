
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
            for child in item.equipment_id.get_all_childs():
                if child.production_lot:
                    lots.append(child.production_lot.id)
            item.componentes = lots

    
    componentes = fields.One2many(compute=_get_componentes_from_equipment, comodel_name="stock.lot", inverse_name="plan_id", string="Componentes")