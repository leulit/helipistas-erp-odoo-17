
from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class MaintenancePlan(models.Model):
    _inherit = "maintenance.plan"


    def unlink(self):
        if not self.env.user.has_group("leulit.RolIT_developer"):
            raise UserError("Para eliminar un Programa de mantenimiento contacte con el departamento IT.")
        return super(MaintenancePlan, self).unlink()

    def copy(self, default=None):
        default = default or {}
        default.update({'parent_id': self.id, 'state': 'pendiente'})
        new_plan = super(MaintenancePlan, self).copy(default)
        for item in self.planned_activity_ids:
            item.copy(default={'maintenance_plan_id': new_plan.id})
        return new_plan

    def copy_for_new_helicopter(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20241113_1600_form')
        view_id = view_ref and view_ref[1] or False
        context = {'default_maintenance_plan_id':self.id}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuevo Plan de Mantenimiento',
            'res_model': 'leulit.wizard_copy_plan',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context' : context,
        }

    def create_all_job_cards(self):
        for item in self.planned_activity_ids:
            if not item.job_card_id:
                item.action_generar_job_card()

    def _get_is_activable(self):
        for item in self:
            item.is_activable = False
            if item.state == 'pendiente':
                item.is_activable = True
                if self.parent_id:
                    for request in self.parent_id.maintenance_ids:
                        if request.stage_id.id in [1,2]:
                            item.is_activable = False


    parent_id = fields.Many2one(comodel_name="maintenance.plan", string="Plan de matenimiento previo")
    state = fields.Selection(selection=[('pendiente','Pendiente'),('activo','Activo'),('archivado','Archivado')], string='Estado', default='pendiente')
    is_activable = fields.Boolean(compute=_get_is_activable, string='')
    planned_activity_ids = fields.One2many("maintenance.planned.activity", "maintenance_plan_id", "Planned Activities")

    def pending_status_plan(self):
        self.state = 'pendiente'


    def activate_plan(self):
        if self.parent_id:
            self.parent_id.state = 'archivado'
        self.state = 'activo'


    def create_plan_activity(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','maintenance_planned_activity_view_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_maintenance_plan_id': self.id,
            'default_activity_type_id': self.env['mail.activity.type'].search([('name','=','Petición de mantenimiento')],limit=1).id,
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actividad programada',
            'res_model': 'maintenance.planned.activity',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }
    

    def open_wizard_create_request(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230505_1518_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_rel_maintenance_plan': self.id,
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Orden de Trabajo',
            'res_model': 'leulit.wizard_create_maintenance_request',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }
    

    def open_maintenance_request(self):
        action = self.env['ir.actions.act_window']._for_xml_id('leulit_taller.leulit_20231020_1222_action')
        action['domain'] = [('id', 'in', self.maintenance_ids.ids)]
        return action


    def add_task_in_wo(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20240208_1003_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_rel_maintenance_plan': self.id,
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Añadir tareas a Orden de Trabajo',
            'res_model': 'leulit.wizard_add_task_request',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }
