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
        items = self.env['stock.move.line'].search([('equipment_id','=',self.id)])

        view_ref = self.env['ir.model.data'].get_object_reference('leulit_almacen', 'leulit_20230112_1533_tree')
        view_id = view_ref and view_ref[1] or False
        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Movimientos',
           'res_model'      : 'stock.move.line', 
           'view_id'        : view_id,
           'view_type'      : 'form',
           'view_mode'      : 'tree',
           'domain'         : [('id', 'in', items.ids)],
        }
