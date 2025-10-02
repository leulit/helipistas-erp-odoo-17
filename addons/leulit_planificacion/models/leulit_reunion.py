# -*- encoding: utf-8 -*-

from importlib.util import set_loader
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_reunion(models.Model):
    _name = "leulit.reunion"
    _order = "fecha_ini desc"
    _rec_name = "asunto"


    def unlink(self):
        for item in self:
            if item.resource_fields:
                for resource in item.resource_fields:
                    resource.unlink()
            if item.rel_meeting:
                item.rel_meeting.unlink()
        return super(leulit_reunion, self).unlink()


    @api.onchange('hora_inicio_evento', 'duration')
    def onchange_horas(self):
        for item in self:
            if item.hora_inicio_evento and item.duration:
                item.hora_fin_evento = item.hora_inicio_evento + item.duration


    def finalizar_reunion(self):
        for item in self:
            item.end_meeting = True


    def action_tasks(self):
        return {
            'name': 'Tasks',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'tree,form',
            'domain': [('reunion_id', '=', self.id)],
        }

    def create_task(self):
        self.ensure_one()
        view = self.env.ref('leulit_planificacion.leulit_wizard_reunion_create_task',raise_if_not_found=False)

        project = self.env['project.project'].search([('name','=','Reuniones')])

        context = {
            'default_name': self.asunto,
            'default_project_id': project.id,
            'default_reunion_id': self.id,
            'default_company_id': self.env.company.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Task',
            'res_model': 'leulit.wizard_claim_create_task',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'context': context,
        }


    @api.depends('fecha_ini')
    def _get_recursos_ocupados(self):
        for item in self:
            recursos = self.env['leulit.event_resource'].search([('fecha_ini', '=', item.fecha_ini),('type','=','persona')])
            if recursos:
                item.recursos_ocupados = recursos
            else:
                item.recursos_ocupados = False


    def _get_tipo_reunion(self):
        for item in self:
            if item.tipo_meeting:
                tipo_reunion = ''
                for tipo in item.tipo_meeting:
                    tipo_reunion += tipo.name + "; "
                item.tipo_reunion = tipo_reunion
            else:
                item.tipo_reunion = ""


    @api.depends('fecha_ini')
    def _get_recursos_disponibles(self):
        for item in self:
            item.recursos_disponibles = self.env['leulit.event_resource'].search([('fecha_ini', '=', item.fecha_ini),('type','=','persona')])
        

    @api.depends('asistentes')
    def _is_mine(self):
        for item in self:
            item.is_mine = False
            if item.user_id and item.user_id.id == self.env.uid:
                item.is_mine = True
            elif len(item.asistentes) > 0:
                for asistente in item.asistentes:
                    if asistente.user_id and asistente.user_id.id == self.env.uid:
                        item.is_mine = True


    def search_is_mine(self, operator, value):
        ids = []
        for item in self.search([]):
            if item.user_id and item.user_id.id == self.env.uid:
                ids.append(item.id)
            else:
                for asistente in item.asistentes:
                    if asistente.user_id and asistente.user_id.id == self.env.uid:
                        ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]


    @api.depends('asistentes')
    def _pendiente(self):
        for item in self:
            item.pendiente = False
            for asistente in item.asistentes:
                if not asistente.asistencia:
                    item.pendiente = True

    @api.depends('asistentes')
    def _pendiente_mine(self):
        for item in self:
            item.pendiente_mine = False
            for asistente in item.asistentes:
                if asistente.user_id.id == self.env.uid:
                    if not asistente.asistencia:
                        item.pendiente_mine = True
    
    @api.depends('task_ids')
    def _compute_task_count(self):
        for item in self:
            item.task_count = len(item.task_ids)
    

    asunto = fields.Char('Asunto',required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    tipo_meeting = fields.Many2many('leulit.tipo_meeting', 'leulit_rel_meeting_tipo_meeting','meeting_rel', 'tipo_meeting_rel', 'Tipo reunión')
    documentos = fields.Many2many('ir.attachment', 'leulit_meeting_rel', 'meeting_rel', 'doc_rel', 'Documentos')
    end_meeting = fields.Boolean('Reunión Finalizada')
    cliente = fields.Many2one('res.partner', 'Cliente', domain=[('customer_rank','=','1'), ('parent_id', '=', False)])
    presupuesto_id = fields.Many2one('sale.order', 'Presupuesto')
    allday = fields.Boolean('¿Todo el día?')
    descripcion = fields.Html('Descripción',required=True)
    location = fields.Char('Lugar',required=True)
    user_id = fields.Many2one('res.users', 'Responsable',required=True,default=lambda self: self.env.uid)
    resource_fields = fields.One2many('leulit.event_resource', 'reunion', 'Recurso')
    recursos_ocupados = fields.One2many('leulit.event_resource','reunion',string='Recursos Ocupados',store=False,compute='_get_recursos_ocupados')
    hora_inicio_evento = fields.Float("Hora inicio",required=True,default=9.00)
    hora_fin_evento = fields.Float("Hora fin",required=True,default=10.00)
    fecha_ini = fields.Date('Fecha',required=True,default=fields.Date.context_today)
    duration = fields.Float("Duración",required=True,default=1.00)
    rel_meeting = fields.Many2one('calendar.event','Meeting')
    acta_reunion = fields.Text("Acta Reunión")
    # work_order = fields.Many2one('leulit.work_order','Work order')
    tipo_reunion = fields.Text(compute='_get_tipo_reunion',string='Tipo de reunión')
    asistentes = fields.One2many('leulit.reunion_asistente', 'reunion_id', 'Asistentes')
    recursos_disponibles = fields.One2many(compute='_get_recursos_disponibles', comodel_name="leulit.event_resource", string="Recursos Ocupados", store=False)
    is_mine = fields.Boolean(compute=_is_mine,string='Asignada',store=False,search=search_is_mine)
    
    pendiente_mine = fields.Boolean(compute='_pendiente_mine',string='',store=False)
    pendiente = fields.Boolean(compute='_pendiente',string='',store=False)
    task_ids = fields.One2many('project.task', 'reunion_id', string='Tasks')
    task_count = fields.Integer(compute=_compute_task_count, string='Task Count')


class WizardReunionCreateTask(models.TransientModel):
    _name = "leulit.wizard_reunion_create_task"
    _description = "leulit_wizard_reunion_create_task"

    name = fields.Char("Titulo Tarea")
    project_id = fields.Many2one("project.project", "Project")
    date_deadline = fields.Date("Deadline")
    user_id = fields.Many2one("res.users", "Assigned to",default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", "Compañía")
    partner_id = fields.Many2one("res.partner", "Cliente")

    def create_task(self):
        task = self.env["project.task"].create({
            "name": self.name,
            "project_id": self.project_id.id or False,
            "date_deadline": self.date_deadline or False,
            "user_id": self.user_id.id or False,
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
        })
        return task