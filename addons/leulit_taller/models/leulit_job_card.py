from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class LeulitJobCard(models.Model):
    _name = "leulit.job_card"
    _rec_name = "descripcion"


    # def change_equipamiento_id(self):
    #     """Abre la vista leulit_20250717_1023_form como popup para este registro."""
    #     self.ensure_one()
    #     view_ref = self.env.ref('leulit_taller.leulit_20250717_1023_form')
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Cambiar equipamiento',
    #         'res_model': 'leulit.job_card',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'res_id': self.id,
    #         'view_id': view_ref.id,
    #         'target': 'new',  # Esto hace que sea popup/modal
    #         'context': dict(self.env.context),
    #     }

    descripcion = fields.Char(string="Descripción")
    activity_planned_id = fields.Many2one(comodel_name="maintenance.planned.activity", string="Ítem de Plan de Mantenimiento")
    equipamiento_id = fields.Many2one(related="activity_planned_id.equipment_id_maintenance_plan", comodel_name="maintenance.equipment", string="Equipo", store=True)
    maintenance_plan_id = fields.Many2one(related="activity_planned_id.maintenance_plan_id", comodel_name="maintenance.plan", string="Plan de Matenimiento")
    task_id = fields.Many2one(comodel_name="project.task", domain="[('maintenance_request_id','!=',False)]", string="Tarea de Orden de Trabajo")
    job_card_item_ids = fields.One2many(comodel_name="leulit.job_card_item", inverse_name="job_card_id", string="Job Card Items")
    parent_section_id = fields.Many2one(comodel_name="leulit.job_card", string="Job Card")
    sections_ids = fields.One2many(comodel_name="leulit.job_card", inverse_name="parent_section_id", string="Secciones")

    # def copy(self, default=None):
    #     default = dict(default or {})
    #     default['maintenance_plan_id'] = False
    #     default['equipamiento_id'] = False
    #     default['activity_planned_id'] = False
    #     default['task_id'] = False
    #     # Duplicar los items relacionados
    #     new_job_card = super().copy(default)
    #     for item in self.job_card_item_ids:
    #         item.copy(default={'job_card_id': new_job_card.id, 'equipamiento_id': False})
    #     # Duplicar las secciones relacionados
    #     for section in self.sections_ids:
    #         section.copy(default={'parent_section_id': new_job_card.id})
    #     return new_job_card