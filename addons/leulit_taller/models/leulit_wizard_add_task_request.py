# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


    
class leulit_wizard_add_task_request(models.TransientModel):
    _name           = "leulit.wizard_add_task_request"
    _description    = "leulit_wizard_add_task_request"


    def add_task_request(self):
        for item in self:
            tag_id = self.env['project.tags'].search([('name','=','Tareas de mantenimiento')])
            company = self.env['res.company'].search([('name','ilike','Icarus')])
            def create_tasks_from_job_card(planned_task, project_task, items, request, tag_id, tsn):
                for item_jc in items:
                    sub_tarea = self.env['project.task'].with_context(tracking_disable=True).create({
                        'name' : item_jc.descripcion,
                        'company_id' : company.id,
                        'project_id' : int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project')),
                        'user_id' : self.env['res.users'].search([('name','=','Albert Petanas')]).id,
                        'maintenance_equipment_id' : item_jc.equipamiento_id.id,
                        'maintenance_request_id' : request.id,
                        'tipo_tarea_taller' : planned_task.tipo,
                        'parent_id' : project_task.id,
                        'item_job_card_id' : item_jc.id,
                        'assignment_date' : datetime.now(),
                        'production_lot_id' : item_jc.equipamiento_id.production_lot.id,
                        'tag_ids': tag_id.ids,
                        'type_maintenance': item_jc.type_maintenance,
                        'ata_ids': item_jc.ata_ids.ids,
                        'certificacion_ids': item_jc.certificacion_ids.ids,
                        'manuales_ids': item_jc.manual_id.ids
                    })
                    if item_jc.no_aplica:
                        stage_id = self.env['project.task.type'].search([('project_ids','in',[int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))]),('name','=','N/A')])
                        sub_tarea.stage_id = stage_id.id
                    if item_jc.oblig_form_one:
                        form_one_today = self.env['leulit.maintenance_form_one'].search([('fecha','=',datetime.now().date())])
                        sequence_form_one = 1
                        if len(form_one_today) > 0:
                            sequence_form_one = len(form_one_today)+1
                        name_form_one = 'ICM-'+datetime.now().strftime("%y%m%d")+'-'+str(sequence_form_one)
                        self.env['leulit.maintenance_form_one'].create({
                            'tracking_number' : name_form_one,
                            'work_order_id': request.id,
                            'fecha': datetime.now().date(),
                            'task_id': sub_tarea.id
                        })
                    if item_jc.boroscopia:
                        self.env['leulit.maintenance_boroscopia'].create({
                            'request': request.id,
                            'fecha': datetime.now().date(),
                            'tsn': tsn,
                            'task': sub_tarea.id
                        })
            for task in item.tasks_plan:
                tarea = self.env['project.task'].with_context(tracking_disable=True).create({
                    'name' : task.descripcion,
                    'description' : task.tarea_preventiva_id.referencia,
                    'company_id' : company.id,
                    'project_id' : int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project')),
                    'user_id' : self.env['res.users'].search([('name','=','Albert Petanas')]).id,
                    'maintenance_equipment_id' : task.equipment_id.id,
                    'maintenance_planned_activity_id' : task.id,
                    'maintenance_request_id' : item.rel_maintenance_request.id,
                    'tipo_tarea_taller' : task.tipo,
                    'assignment_date' : datetime.now(),
                    'production_lot_id' : task.equipment_id.production_lot.id,
                    'tag_ids': tag_id.ids,
                    'service_bulletin_id': task.service_bulletin_id.id if task.service_bulletin_id else False,
                    'airworthiness_directive_id': task.airworthiness_directive_id.id if task.airworthiness_directive_id else False,
                })
                if task.job_card_id:
                    if task.job_card_id.sections_ids:
                        for section in task.job_card_id.sections_ids:
                            section_tarea = self.env['project.task'].with_context(tracking_disable=True).create({
                                'name' : section.descripcion,
                                'company_id' : company.id,
                                'project_id' : int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project')),
                                'user_id' : self.env['res.users'].search([('name','=','Albert Petanas')]).id,
                                'maintenance_equipment_id' : task.equipment_id.id,
                                'maintenance_request_id' : item.rel_maintenance_request.id,
                                'tipo_tarea_taller' : task.tipo,
                                'parent_id' : tarea.id,
                                'assignment_date' : datetime.now(),
                                'production_lot_id' : task.equipment_id.production_lot.id,
                                'tag_ids': tag_id.ids,
                            })
                            create_tasks_from_job_card(task, section_tarea, section.job_card_item_ids, item.rel_maintenance_request, tag_id, item.rel_maintenance_plan.equipment_id.helicoptero.airtime)
                    else:
                        create_tasks_from_job_card(task, tarea, task.job_card_id.job_card_item_ids, item.rel_maintenance_request, tag_id, item.rel_maintenance_plan.equipment_id.helicoptero.airtime)


    rel_maintenance_plan = fields.Many2one(comodel_name='maintenance.plan', string='Plan de Mantenimiento', required=True)
    tasks_plan = fields.Many2many('maintenance.planned.activity', relation='leulit_wizard_add_task_rel_planned_activity', column1='wizard_add_task_request_id', column2='planned_activity_id', string='Tareas')
    rel_maintenance_request = fields.Many2one(comodel_name='maintenance.request', string='Work Order', required=True, domain="[('maintenance_plan_id','=',rel_maintenance_plan),('done','=',False)]")


    @api.onchange('rel_maintenance_plan','rel_maintenance_request')
    def _onchange_rel_maintenance_plan(self):
        for record in self:
            t_planificadas_wo = self.env['project.task'].search([('maintenance_request_id','=',record.rel_maintenance_request.id),('tipo_tarea_taller','!=','defecto_encontrado'),('parent_id','=',False)])
            record.tasks_plan = False
            return {'domain': {'tasks_plan': [('maintenance_plan_id','=',record.rel_maintenance_plan.id),('task_ids','not in',t_planificadas_wo.ids)]}}