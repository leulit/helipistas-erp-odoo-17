# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class leulit_wizard_copy_plan(models.TransientModel):
    _name           = "leulit.wizard_copy_plan"
    _description    = "leulit_wizard_copy_plan"

    def copy_for_new_helicopter(self):
        new_plan = self.maintenance_plan_id.copy()
        new_plan.equipment_id = self.equipment_id.id
        new_plan.parent_id = False
        for planned_act in new_plan.planned_activity_ids:
            new_job_card = planned_act.job_card_id.copy({'activity_planned_id': planned_act.id})
            for item in planned_act.job_card_id.job_card_item_ids:
                equipment_id = False
                if item.equipamiento_id.is_motor:
                    equipment_id = self.equipment_id.get_motor().id
                item.copy({'job_card_id': new_job_card.id,'equipamiento_id':equipment_id})
            for section in planned_act.job_card_id.sections_ids:
                new_section = section.copy({'parent_section_id': new_job_card.id})
                for item in section.job_card_item_ids:
                    equipment_id = False
                    if item.equipamiento_id.is_motor:
                        equipment_id = self.equipment_id.get_motor().id
                    item.copy({'job_card_id': new_section.id,'equipamiento_id':equipment_id})
            planned_act.job_card_id = new_job_card.id


        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20231020_1300_form')
        view_id = view_ref and view_ref[1] or False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Plan de Mantenimiento',
            'res_model': 'maintenance.plan',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': new_plan.id,
            'target': 'current',
        }

    maintenance_plan_id = fields.Many2one(comodel_name='maintenance.plan', string='Plan de Mantenimiento', required=True)
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipo', required=True)