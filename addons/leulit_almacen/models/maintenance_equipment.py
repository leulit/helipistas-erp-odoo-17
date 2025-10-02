# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"
    

    def open_move_lines_to_equipment(self):
        self.ensure_one()
        view = self.env.ref('leulit_almacen.leulit_20230112_1533_tree',raise_if_not_found=False)
        items = self.env['stock.move.line'].search([('equipment_id','=',self.id)])

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Movimientos',
           'res_model'      : 'stock.move.line', 
           'view_id'        : view.id if view else False,
           'view_type'      : 'form',
           'view_mode'      : 'tree',
           'domain'         : [('id', 'in', items.ids)],
        }
