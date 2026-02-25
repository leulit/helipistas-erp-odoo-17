from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.sql_db import db_connect
import logging
import threading

_logger = logging.getLogger(__name__)


class LeulitJobCard(models.Model):
    _name = "leulit.job_card"
    _description = 'Tarjeta de Trabajo de Mantenimiento'
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
    # referencia = fields.Char(related="activity_planned_id.reference", string="Referencia", store=True)
    equipamiento_id = fields.Many2one(related="activity_planned_id.equipment_id_maintenance_plan", comodel_name="maintenance.equipment", string="Equipo", store=True)
    maintenance_plan_id = fields.Many2one(related="activity_planned_id.maintenance_plan_id", comodel_name="maintenance.plan", string="Plan de Matenimiento")
    task_id = fields.Many2one(comodel_name="project.task", domain="[('maintenance_request_id','!=',False)]", string="Tarea de Orden de Trabajo")
    job_card_item_ids = fields.One2many(comodel_name="leulit.job_card_item", inverse_name="job_card_id", string="Job Card Items")
    parent_section_id = fields.Many2one(comodel_name="leulit.job_card", string="Job Card")
    sections_ids = fields.One2many(comodel_name="leulit.job_card", inverse_name="parent_section_id", string="Secciones")

    def upd_job_card_planned_activities(self):
        """Lanza un thread para actualizar job_card_id en maintenance.planned.activity"""
        _logger.error("upd_job_card_planned_activities iniciando")
        threaded_calculation = threading.Thread(target=self.run_upd_job_card_planned_activities, args=([]))
        _logger.error("############################################# upd_job_card_planned_activities start thread")
        threaded_calculation.start()
        return {}

    def run_upd_job_card_planned_activities(self):
        """Actualiza el campo job_card_id en todos los registros de maintenance.planned.activity"""
        new_cr = db_connect(self.env.cr.dbname).cursor()
        try:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            # Obtener todos los registros de leulit.job_card
            for job_card in env['leulit.job_card'].search([('maintenance_plan_id','=',33)]):
                # Si el job_card tiene un activity_planned_id relacionado
                if job_card.activity_planned_id:
                    # Actualizar el campo job_card_id en maintenance.planned.activity
                    job_card.activity_planned_id.write({
                        'job_card_id': job_card.id
                    })
            new_cr.commit()
        except Exception as e:
            _logger.error("Error en upd_job_card_planned_activities: %s", str(e))
            new_cr.rollback()
        finally:
            new_cr.close()
        _logger.error("############################################# upd_job_card_planned_activities fin")

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


