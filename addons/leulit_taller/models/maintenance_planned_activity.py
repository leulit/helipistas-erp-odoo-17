# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MiantenancePlannedactivity(models.Model):
    _name = "maintenance.planned.activity"
    _description = "Maintenance Planned Activity"
    _rec_name = "descripcion"

    @api.depends('tarea_preventiva_id','left_h','right_h')
    def _get_name(self):
        for item in self:
            item.descripcion = item.tarea_preventiva_id.descripcion
            if item.comentario_descripcion:
                item.descripcion = "{0} ({1})".format(item.descripcion,item.comentario_descripcion)
            if item.left_h:
                item.descripcion = "{0} LH".format(item.descripcion)
            if item.right_h:
                item.descripcion = "{0} RH".format(item.descripcion)

    @api.depends('maintenance_plan_id','horas_next_due','fecha_next_due')
    def _get_remaining(self):
        for item in self:
            item.horas_remaining = 0
            item.days_remaining = 0
            if item.maintenance_plan_id:
                tsn = item.maintenance_plan_id.equipment_id.airtime_helicopter
                if item.horas_next_due != 0:
                    item.horas_remaining = item.horas_next_due - tsn
                if item.fecha_next_due:

                    item.days_remaining = (item.fecha_next_due - datetime.now().date()).days

            
    @api.depends('horas_last_done','int_h','fecha_last_done','float_interval','tag_interval')
    def _get_next_due(self):
        for item in self:
            item.horas_next_due = 0
            item.fecha_next_due = False
            if item.horas_last_done and item.int_h:
                item.horas_next_due = item.horas_last_done + item.int_h
            if item.fecha_last_done and item.float_interval:
                if item.tag_interval == 'M':
                    item.fecha_next_due = item.fecha_last_done + relativedelta(months=item.float_interval)
                if item.tag_interval == 'Y':
                    item.fecha_next_due = item.fecha_last_done + timedelta(days=item.float_interval*365)


    @api.depends('float_interval','tag_interval','char_interval')
    def _get_interval(self):
        for item in self:
            item.interval = ''
            if item.float_interval and item.tag_interval:
                item.interval = "{0} {1}".format(int(item.float_interval),item.tag_interval)
            if item.char_interval:
                item.interval = item.char_interval


    @api.depends('horas_remaining','aviso_horas','alarma_horas')
    def _get_semaforo_horas(self):
        for item in self:
            item.semaforo_horas = ''
            if item.aviso_horas and item.alarma_horas:
                item.semaforo_horas = 'green'
                if item.horas_remaining < item.aviso_horas:
                    item.semaforo_horas = 'yellow'
                if item.horas_remaining < item.alarma_horas:
                    item.semaforo_horas = 'red'
                

    @api.depends('days_remaining','aviso_dias','alarma_dias')
    def _get_semaforo_dias(self):
        for item in self:
            item.semaforo_dias = ''
            if item.aviso_dias and item.alarma_dias:
                item.semaforo_dias = 'green'
                if item.days_remaining < item.aviso_dias:
                    item.semaforo_dias = 'yellow'
                if item.days_remaining < item.alarma_dias:
                    item.semaforo_dias = 'red'
    
    @api.onchange('left_h')
    def onchange_lh(self):
        if self.left_h:
            self.right_h = False

    @api.onchange('right_h')
    def onchange_rh(self):
        if self.right_h:
            self.left_h = False

    activity_type_id = fields.Many2one("mail.activity.type", "Activity Type", required=True)
    user_id = fields.Many2one("res.users", "Responsible", default=lambda self: self.env.user)
    date_before_request = fields.Integer("# Days before request",help="This is the number of days the due date of the activity will be""set before the Maintenance request scheduled date",)
    maintenance_plan_id = fields.Many2one("maintenance.plan", "Maintenance Plan")

    tarea = fields.Char(string="Task")
    int_h = fields.Float(string="Int H")
    interval = fields.Char(compute=_get_interval, string="Interval")
    char_interval = fields.Char(string="Interval Texto")
    float_interval = fields.Float(string="Interval Numero")
    tag_interval = fields.Selection(selection=[('M','Meses'),('Y','Años')],string="")
    tarea_preventiva_id = fields.Many2one(comodel_name="leulit.maintenance_task_preventive", string="Descripción")
    referencia = fields.Char(related="tarea_preventiva_id.referencia", string="Referencia")
    horas_last_done = fields.Float(string="Horas L.")
    fecha_last_done = fields.Date(string="Fecha L.")
    horas_next_due = fields.Float(compute=_get_next_due, string="Horas N.")
    fecha_next_due = fields.Date(compute=_get_next_due, string="Fecha N.")
    horas_remaining = fields.Float(compute=_get_remaining, string="Horas R.")
    days_remaining = fields.Integer(compute=_get_remaining, string="Dias R.")
    
    aviso_horas = fields.Float(string="Aviso horas")
    alarma_horas = fields.Float(string="Alarma horas")
    aviso_dias = fields.Float(string="Aviso dias")
    alarma_dias = fields.Float(string="Alarma dias")

    semaforo_horas = fields.Char(compute=_get_semaforo_horas, string=" ")
    semaforo_dias = fields.Char(compute=_get_semaforo_dias, string=" ")
    task_ids = fields.One2many(comodel_name="project.task", inverse_name="maintenance_planned_activity_id", string="Tareas")
    tipo = fields.Selection(selection=[('tarea','Tarea'),('service_bulletin','Service Bulletin'),('airworthiness_directive','Airworthiness Directive')], default="tarea" , string="Tipo")
    equipment_id_maintenance_plan = fields.Many2one(related="maintenance_plan_id.equipment_id", string="Equipamiento del plan de mantenimiento", store=True)
    equipment_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipamiento")
    job_card_id = fields.Many2one(comodel_name="leulit.job_card", string="Job card")
    service_bulletin_id = fields.Many2one(comodel_name="leulit.service_bulletin", string="Service Bulletin", domain="[('apply','=',True)]")
    airworthiness_directive_id = fields.Many2one(comodel_name="leulit.airworthiness_directive", string="Airworthiness Directive", domain="[('apply','=',True)]")
    doble_check = fields.Boolean(string='Doble check')
    inspeccion_seguridad = fields.Boolean(string='Inspección seguridad')
    oblig_form_one = fields.Boolean(string='Obligatoriedad Form One')
    sequence = fields.Integer(string='Sequence', default=10)
    notas = fields.Text(string='Notas')
    left_h = fields.Boolean(string='LH')
    right_h = fields.Boolean(string='RH')
    comentario_descripcion = fields.Char(string='Añadido a la descripción')
    descripcion = fields.Char(compute=_get_name, string='Descripción')


    def open_planned_activity(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','maintenance_planned_activity_view_form')
        view_id = view_ref and view_ref[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitud',
            'res_model': 'maintenance.planned.activity',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': self.id,
            'target': 'current',
        }
    

    def action_generar_job_card(self):
        job_card = self.env['leulit.job_card'].create({
            'descripcion': self.descripcion,
            'activity_planned_id': self.id,
        })
        self.job_card_id = job_card.id



