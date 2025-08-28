# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, api, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task"]


    @api.onchange('stage_id')
    def onchange_stage_manintenance_task(self):
        if self.maintenance_request_id:
            if self.maintenance_request_id.accepted:
                if self._origin and self.maintenance_request_id:
                    if (self.stage_id.name == 'Pendiente' or self.stage_id.name == 'En proceso') and (self._origin.stage_id.name == 'Realizada' or self._origin.stage_id.name == 'N/A' or self._origin.stage_id.name == 'Pospuesta'):
                        if not self.env.user.has_group("leulit.RolIT_developer") and self.maintenance_request_done:
                            raise UserError("Una vez finalizada la work order no se puede abrir de nuevo la tarea, en caso de error contactar con IT.")
                if self.maintenance_request_id and self.stage_id.name == 'Pospuesta':
                    if not self.env.user.has_group("leulit.RCAMO_base"):
                        raise UserError("Para cambiar de estado la tarea a 'Pospuesta' lo ha de hacer el departamento CAMO.")
                    else:
                        for child in self._origin.child_ids:
                            stage_id = self.env['project.task.type'].search([('project_ids','in',[self.project_id.id]),('name','=','Pospuesta')])
                            child.stage_id = stage_id.id
                if self.maintenance_request_id and self.stage_id.name == 'Realizada':
                    if not self.child_ids:
                        if not self.ata_ids:
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia rellenar antes el campo 'ATAs' para continuar.")
                        if not self.certificacion_ids:
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia rellenar antes el campo 'Certificaciones' para continuar.")
                        if not self.tipos_actividad:
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia rellenar antes el campo 'Tipo actividad mecánico' para continuar.")
                        if not self.type_maintenance:
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia rellenar antes el campo 'Tipo' para continuar.")
                    self.user_id = self.env.user.id
                    if self.tipo_tarea_taller == 'defecto_encontrado':
                        if self.solucion_defecto == False or self.solucion_defecto == '':
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia rellenar antes el campo 'Solución Defecto' para continuar.")
                    if self.tipo_tarea_taller != 'tarea':
                        if len(self.manuales_ids) == 0:
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia añadir un manual para continuar.")
                    if self.doble_check_ata or self.doble_check_intern:
                        if len(self.double_check_ids) > 0:
                            for doble_check in self.double_check_ids:
                                if not doble_check.first_doble_check or not doble_check.second_doble_check:
                                    raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Doble check' para continuar.")
                        else:
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Doble check' para continuar.")
                        if len(self.security_inspection_ids) > 0:
                            for inspection in self.security_inspection_ids:
                                if not inspection.first_inspeccion_seguridad or not inspection.second_inspeccion_seguridad:
                                    raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Inspección de seguridad' para continuar.")
                        else:
                            raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Inspección de seguridad' para continuar.")
                    if self.item_job_card_id:
                        if self.item_job_card_id.doble_check:
                            if len(self.double_check_ids) > 0:
                                for doble_check in self.double_check_ids:
                                    if not doble_check.first_doble_check or not doble_check.second_doble_check:
                                        raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Doble check' para continuar.")
                            else:
                                raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Doble check' para continuar.")
                        # if not self.item_job_card_id.doble_check and not self.doble_check_ata:
                        #     self.second_user_doble_check = self.user_id.id
                        if self.item_job_card_id.inspeccion_seguridad:
                            if len(self.security_inspection_ids) > 0:
                                for inspection in self.security_inspection_ids:
                                    if not inspection.first_inspeccion_seguridad or not inspection.second_inspeccion_seguridad:
                                        raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Inspección de seguridad' para continuar.")
                            else:
                                raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia marcar antes el campo 'Inspección de seguridad' para continuar.")
                        if self.item_job_card_id.tiempo_defecto == 0:
                            if not self.timesheet_ids:
                                raise UserError("Para cambiar de estado la tarea a 'Realizada' deberia imputar tiempo manualmente para continuar.")
                        else:
                            if not self.timesheet_ids:
                                self.env['account.analytic.line'].create({
                                    'date_time':datetime.now(),
                                    'employee_id':self.user_id.employee_id.id,
                                    'name': '['+self.maintenance_request_id.name+']-'+self.name,
                                    'unit_amount': self.item_job_card_id.tiempo_defecto,
                                    'project_id': self.project_id.id,
                                    'task_id': self.id,
                                    'maintenance_request_id': self.maintenance_request_id.id,
                                })
                        if self.item_job_card_id.oblig_form_one:
                            if self.env['leulit.maintenance_form_one'].search([('task_id','!=',self.id)]):
                                form_one_today = self.env['leulit.maintenance_form_one'].search([('fecha','=',datetime.now().date())])
                                sequence_form_one = 1
                                if len(form_one_today) > 0:
                                    sequence_form_one = len(form_one_today)+1
                                name_form_one = 'ICM-'+datetime.now().strftime("%y%m%d")+'-'+str(sequence_form_one)
                                self.env['leulit.maintenance_form_one'].create({
                                    'tracking_number' : name_form_one,
                                    'work_order_id': self.maintenance_request_id.id,
                                    'fecha': datetime.now().date(),
                                    'task_id': self._origin.id
                                })
                    # else:
                    #     if not self.doble_check_ata:
                    #         self.second_user_doble_check = self.user_id.id
                    if self.parent_id:
                        length = 1
                        for child in self.parent_id.child_ids:
                            if child.id != self.id:
                                if child.stage_id.name not in ['En proceso','Pendiente']:
                                    length += 1
                        if length == len(self.parent_id.child_ids):
                            self.parent_id.user_id = self.user_id.id
                            stage_id = self.env['project.task.type'].search([('project_ids','in',[self.project_id.id]),('name','=','Realizada')])
                            self.parent_id.stage_id = stage_id.id
                    for child in self.child_ids:
                        if child.stage_id.name not in ['Realizada','N/A']:
                            raise UserError("Esta tarea tiene subtareas sin realizar.")
                    self.finish_date = datetime.now()
            else:
                raise UserError("Para cambiar de estado la tarea, la Work Order no debe estar en estado 'Nueva solicitud'.")

    
    def unlink(self):
        for item in self:
            if item.maintenance_request_id and item.maintenance_planned_activity_id:
                if not self.env.user.has_group("leulit.RCAMO_base"):
                    raise UserError("Para eliminar la tarea contacte con el departamento CAMO.")
            if item.maintenance_request_id:
                if item.child_ids:
                    item.child_ids.unlink()

        return super(ProjectTask, self).unlink()


    @api.depends('child_ids')
    def _get_semaforo_subtasks(self):
        for item in self:
            item.semaforo_subtasks = 'green'
            for child in item.child_ids:
                if child.stage_id.name in ['En proceso','Pendiente']:
                    item.semaforo_subtasks = 'red'


    @api.depends('stage_id')
    def _get_realizada_maintenance_task(self):
        for item in self:
            item.estado_tarea_bool_realizada = False
            if item.stage_id.name == 'Realizada':
                item.estado_tarea_bool_realizada = True


    @api.depends('stage_id')
    def _get_noaplica_maintenance_task(self):
        for item in self:
            item.estado_tarea_bool_noaplica = False
            if item.stage_id.name == 'N/A':
                item.estado_tarea_bool_noaplica = True


    @api.depends('maintenance_request_id')
    def _get_is_done_maintenance_request(self):
        for item in self:
            item.maintenance_request_done = False
            if item.maintenance_request_id:
                if item.maintenance_request_id.done:
                    item.maintenance_request_done = True


    @api.depends('ata_ids','item_job_card_id')
    def _get_doble_check_from_ata(self):
        for item in self:
            item.doble_check_ata = False
            if item.ata_ids:
                for ata in item.ata_ids:
                    if ata.doble_check:
                        item.doble_check_ata = True


    @api.onchange('item_job_card_id')
    def onchange_item_job_card(self):
        tag_id = self.env['project.tags'].search([('name','=','Tareas de mantenimiento')])
        if self.item_job_card_id:
            self.write({
                'maintenance_equipment_id' : self.item_job_card_id.equipamiento_id.id,
                'name' : self.item_job_card_id.descripcion,
                'solucion_defecto' : self.item_job_card_id.solucion,
                'production_lot_id' : self.item_job_card_id.equipamiento_id.production_lot.id,
                'type_maintenance' : self.item_job_card_id.type_maintenance,
                'ata_ids' : self.item_job_card_id.ata_ids.ids,
                'certificacion_ids' : self.item_job_card_id.certificacion_ids.ids,
                'tipos_actividad' : self.item_job_card_id.tipos_actividad.ids,
                'manuales_ids' : self.item_job_card_id.manual_id.ids,
                'tag_ids': tag_id.ids
            })


    @api.onchange('job_card_id')
    def onchange_job_card(self):
        tag_id = self.env['project.tags'].search([('name','=','Tareas de mantenimiento')])
        company = self.env['res.company'].search([('name','ilike','Icarus')])
        if self.job_card_id:
            if not self.external_aircraft:
                if not self.job_card_id.equipamiento_id == self.maintenance_equipment_id:
                    raise UserError("El equipamiento de la Job Card no coincide con el equipamiento de la tarea.")
            self.write({
                'name' : self.job_card_id.descripcion
            })
            for item in self.job_card_id.job_card_item_ids:
                task_1 = self.with_context(tracking_disable=True).create({
                    'parent_id' : self.id,
                    'name' : item.descripcion,
                    'solucion_defecto' : item.solucion,
                    'type_maintenance' : item.type_maintenance,
                    'ata_ids' : item.ata_ids.ids,
                    'certificacion_ids' : item.certificacion_ids.ids,
                    'tipos_actividad' : item.tipos_actividad.ids,
                    'manuales_ids' : item.manual_id.ids,
                    'tag_ids': tag_id.ids,
                    'company_id' : company.id,
                    'user_id' : self.env['res.users'].search([('name','=','Albert Petanas')]).id,
                    'maintenance_request_id' : self.maintenance_request_id.id,
                    'tipo_tarea_taller': 'tarea'
                })
                if not self.external_aircraft:
                    if self.job_card_id.equipamiento_id == self.maintenance_equipment_id:
                        task_1.maintenance_equipment_id = item.equipamiento_id.id if self.maintenance_planned_activity_id else False
                        task_1.production_lot_id = item.equipamiento_id.production_lot.id if self.maintenance_planned_activity_id else False
                else:
                    task_1.maintenance_equipment_id = self.maintenance_equipment_id
            for section in self.job_card_id.sections_ids:
                section_task = self.with_context(tracking_disable=True).create({
                    'parent_id' : self.id,
                    'name' : section.descripcion,
                    'tag_ids': tag_id.ids,
                    'company_id' : company.id,
                    'project_id' : int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project')),
                    'user_id' : self.env['res.users'].search([('name','=','Albert Petanas')]).id,
                    'maintenance_request_id' : self.maintenance_request_id.id,
                    'tipo_tarea_taller': 'tarea'
                })
                for item in section.job_card_item_ids:
                    task_2 = self.with_context(tracking_disable=True).create({
                        'parent_id' : section_task.id,
                        'name' : item.descripcion,
                        'solucion_defecto' : item.solucion,
                        'type_maintenance' : item.type_maintenance,
                        'ata_ids' : item.ata_ids.ids,
                        'certificacion_ids' : item.certificacion_ids.ids,
                        'tipos_actividad' : item.tipos_actividad.ids,
                        'manuales_ids' : item.manual_id.ids,
                        'tag_ids': tag_id.ids,
                        'company_id' : company.id,
                        'user_id' : self.env['res.users'].search([('name','=','Albert Petanas')]).id,
                        'maintenance_request_id' : self.maintenance_request_id.id,
                        'tipo_tarea_taller': 'tarea'
                    })
                    if not self.external_aircraft:
                        if self.job_card_id.equipamiento_id == self.maintenance_equipment_id:
                            task_2.maintenance_equipment_id = item.equipamiento_id.id if self.maintenance_planned_activity_id else False
                            task_2.production_lot_id = item.equipamiento_id.production_lot.id if self.maintenance_planned_activity_id else False
                    else:
                        task_2.maintenance_equipment_id = self.maintenance_equipment_id



    @api.onchange('service_bulletin_id')
    def onchange_service_bulletin(self):
        if self.service_bulletin_id:
            self.write({
                'name' : self.service_bulletin_id.subject + ' [SB- '+ self.service_bulletin_id.name + ']',
            })

    @api.onchange('airworthiness_directive_id')
    def onchange_airworthiness_directive(self):
        if self.airworthiness_directive_id:
            self.write({
                'name' : self.airworthiness_directive_id.subject + ' [AD- '+ self.airworthiness_directive_id.full_name + ']',
            })

    @api.depends('tag_ids')
    def _get_task_maintenance(self):
        tag_id = self.env['project.tags'].search([('name','=','Tareas de mantenimiento')])
        for item in self:
            item.task_maintenance = False
            if item.tag_ids:
                if tag_id in item.tag_ids:
                    item.task_maintenance = True


    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Petición de mantenimiento", ondelete='cascade')
    maintenance_request_done = fields.Boolean(compute=_get_is_done_maintenance_request, string="Petición de mantenimiento cerrada")
    maintenance_equipment_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipamiento")
    external_aircraft = fields.Boolean(related="maintenance_equipment_id.external_aircraft", string="Aeronave externa")
    production_lot_id = fields.Many2one(comodel_name="stock.lot", string="Nº Serie")
    maintenance_planned_activity_id = fields.Many2one("maintenance.planned.activity", "Planned activity")
    tipo_tarea_taller = fields.Selection(selection=[('tarea','Tarea'),('service_bulletin','Service Bulletin'),('airworthiness_directive','Airworthiness Directive'),('defecto_encontrado','Defecto encontrado')], default="tarea" , string="Tipo tarea taller")
    manuales_ids = fields.Many2many(comodel_name='leulit.maintenance_manual', relation='leulit_rel_manual_task', column1='task_id', column2='manual_id', string='Manuales')
    semaforo_subtasks = fields.Char(compute=_get_semaforo_subtasks, string="Semáforo subtareas")
    estado_tarea_bool_realizada = fields.Boolean(compute=_get_realizada_maintenance_task, string="")
    estado_tarea_bool_noaplica = fields.Boolean(compute=_get_noaplica_maintenance_task, string="")
    finish_date = fields.Datetime(string="Fecha de finalización")
    assignment_date = fields.Datetime(string="Fecha de asignación")
    type_maintenance = fields.Selection(selection=[('A', 'A'), ('B', 'B'), ('C','C')], string="Tipo")
    ata_ids = fields.Many2many(comodel_name="leulit.ata", relation="leulit_task_ata" , column1="task_id" , column2="ata_id", string="ATAs")
    certificacion_ids = fields.Many2many(comodel_name="leulit.certificacion", relation="leulit_task_certificacion" , column1="task_id" , column2="certificacion_id", string="Certificaciones")
    job_card_id = fields.Many2one(comodel_name="leulit.job_card", string="Job card", domain="[]")
    item_job_card_id = fields.Many2one(comodel_name="leulit.job_card_item", string="Item de job card")
    doble_check_intern = fields.Boolean(string="Doble check / Inspección de seguridad")
    doble_check_jb = fields.Boolean(related="item_job_card_id.doble_check", string="")
    doble_check_ata = fields.Boolean(compute=_get_doble_check_from_ata, string="")
    inspeccion_seguridad_jb = fields.Boolean(related="item_job_card_id.inspeccion_seguridad", string="")
    double_check_ids = fields.One2many(comodel_name="leulit.maintenance_double_check", inverse_name="task_id", string="Doble Check")
    security_inspection_ids = fields.One2many(comodel_name="leulit.maintenance_security_inspect", inverse_name="task_id", string="Inspección de Seguridad")
    supervisado_por = fields.Many2one(comodel_name="leulit.mecanico", string="Supervisado por")
    solucion_defecto = fields.Char(string="Solución defecto")
    service_bulletin_id = fields.Many2one(comodel_name="leulit.service_bulletin", string="Service bulletin", domain="[('apply','=',True)]")
    airworthiness_directive_id = fields.Many2one(comodel_name="leulit.airworthiness_directive", string="Airworthiness directive", domain="[('apply','=',True)]")
    task_maintenance = fields.Boolean(compute=_get_task_maintenance, string="Tarea de mantenimiento")
    sb_ad_one_time = fields.Boolean(string="SB/AD one time")


    def set_into_workorder(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20240417_1418_form')
        view_id = view_ref and view_ref[1] or False
        context = {
            'default_task': self.id,
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Añadir Tarea a Orden de Trabajo',
            'res_model': 'leulit.wizard_ad_task_to_wo',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }


    def comprobar_estado_wo_tareas(self, request):
        """Comprueba el estado de las tareas de la orden de trabajo"""
        for item in self.search([('maintenance_request_id','=',request)]):
            if item.stage_id.name not in ['Realizada','N/A','Pospuesta']:
                return False
        return True


    def action_open_subtask(self):
        action = self.env["ir.actions.actions"]._for_xml_id("leulit_taller.leulit_20230313_1500_action")

        # display all subtasks of current task
        action['domain'] = [('parent_id', '=', self.id)]

        # update context, with all default values as 'quick_create' does not contains all field in its view
        if self._context.get('default_project_id'):
            default_project = self.env['project.project'].browse(self.env.context['default_project_id'])
        else:
            default_project = self.project_id.subtask_project_id or self.project_id
        ctx = dict(self.env.context)
        ctx = {k: v for k, v in ctx.items() if not k.startswith('search_default_')}
        ctx.update({
            'default_name': self.env.context.get('name', self.name) + ':',
            'default_parent_id': self.id,  # will give default subtask field in `default_get`
            'default_company_id': default_project.company_id.id if default_project else self.env.company.id,
        })

        action['context'] = ctx

        return action



    def open_tarea_editable(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20250724_1244_form')
        view_id = view_ref and view_ref[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarea',
            'res_model': 'project.task',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': self.id,
            'target': 'current',
        }

