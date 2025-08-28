from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class TareaSensibleSeguridad(models.Model):
    _name = 'leulit.tarea_sensible_seguridad'
    _description = 'Tarea sensible para la seguridad'
    _order = "sequence"

    def comprobar_tareas_check(self):
        if self.flag_doble_check:
            tasks_dc = self.env['project.task'].search([('maintenance_request_id','=',self._origin.request_id.id),('double_check_ids','!=',False)])
            if len(tasks_dc) == 0:
                _logger.error('tasks_dc: %s', tasks_dc)
                raise UserError('No puede marcar la tarea como Check porque no hay tareas con doble check.')
        if self.flag_security_inspection:
            tasks_is = self.env['project.task'].search([('maintenance_request_id','=',self._origin.request_id.id),('security_inspection_ids','!=',False)])
            if len(tasks_is) == 0:
                raise UserError('No puede marcar la tarea como Check porque no hay tareas con inspeccion de seguridad.')

    def comprobar_tareas_n_a(self):
        if self.flag_doble_check:
            tasks_dc = self.env['project.task'].search([('maintenance_request_id','=',self._origin.request_id.id),('double_check_ids','!=',False)])
            if len(tasks_dc) > 0:
                _logger.error('tasks_dc: %s', tasks_dc)
                raise UserError('No puede marcar la tarea como N/A porque tiene tareas con doble check.')
        if self.flag_security_inspection:
            tasks_is = self.env['project.task'].search([('maintenance_request_id','=',self._origin.request_id.id),('security_inspection_ids','!=',False)])
            if len(tasks_is) > 0:
                raise UserError('No puede marcar la tarea como N/A porque tiene tareas con inspeccion de seguridad.')

    @api.onchange('no_aplica')
    def onchange_no_aplica(self):
        self.comprobar_tareas_n_a()
        if self.no_aplica:
            self.user_check = self.env.uid
            self.datetime_check = datetime.now()
        else:
            self.user_check = False
            self.datetime_check = False

    @api.onchange('check')
    def onchange_check(self):
        self.comprobar_tareas_check()
        if self.check:
            self.user_check = self.env.uid
            self.datetime_check = datetime.now()
        else:
            self.user_check = False
            self.datetime_check = False

    @api.onchange('d_check')
    def onchange_d_check(self):
        self.comprobar_tareas_check()
        if self.d_check:
            self.user_d_check = self.env.uid
            self.datetime_d_check = datetime.now() + timedelta(minutes=35)
        else:
            self.user_d_check = False
            self.datetime_d_check = False


    name = fields.Char(string="Descripción")
    sequence = fields.Integer("Sequence")
    check = fields.Boolean(string="Check")
    user_check = fields.Many2one(comodel_name="res.users", string="Usuario Check")
    datetime_check = fields.Datetime(string="Fecha Check")
    d_check = fields.Boolean(string="Doble Check")
    user_d_check = fields.Many2one(comodel_name="res.users", string="Usuario Doble Check")
    datetime_d_check = fields.Datetime(string="Fecha Check")
    checklist_id = fields.Many2one(comodel_name="leulit.checklist_tareas_sensibles_seguridad", string="Checklist")
    request_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order Id")
    no_aplica = fields.Boolean(string="N/A")
    flag_doble_check = fields.Boolean(string="Flag Doble Check")
    flag_security_inspection = fields.Boolean(string="Flag Inspección de Seguridad")


    def comprobar_estado_wo_tss(self, request):
        """Comprueba si existen tareas sensibles para la seguridad sin chequear"""
        for item in self.search([('request_id','=',request)]):
            if not item.no_aplica:
                if not item.check or not item.d_check:
                    raise UserError('No puede cerrar esta Orden de Trabajo porque tiene una/s tarea/s sensible para la seguridad sin chequear.')
        return True