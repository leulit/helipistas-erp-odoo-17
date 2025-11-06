# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


class HrTimesheetSwitch(models.TransientModel):
    _name = "hr.timesheet.switch"
    _inherit = "hr.timesheet.switch"


    def _prepare_copy_values(self, record):
        """Return the values that will be overwritten in new timesheet entry."""
        return {
            "name": record.name,
            "date_time": record.date_time,
            "date_time_end": record.date_time_end,
            "project_id": record.project_id.id,
            "task_id": record.task_id.id,
            "unit_amount": 0,
            "employee_id": record.employee_id.id,
            "maintenance_request_id": record.maintenance_request_id.id,
            "vuelo_no_hlp": record.vuelo_no_hlp,
            "vuelo_tipo_act_id": record.vuelo_tipo_act_id,
            "ruta": record.ruta,
            "guardia": record.guardia,
            "unit_amount": record.unit_amount,
            "sale_order": record.sale_order.id,
        }

    def action_switch(self):
        super(HrTimesheetSwitch, self).action_switch()    
        return [
                {"type": "ir.actions.act_window_close"},
                {"type": "ir.actions.act_view_reload"},
            ]

    def _default_project_id(self):
        return self.env['project.project'].search([('name','=','Internal'),('company_id','=',self.env.company.id)])

    def _get_tipo_trabajo(self):
        return (
            ('AOC', 'AOC'),
            ('Trabajo Aereo', 'Trabajo Aereo'),
            ('Escuela', 'Escuela'),
            ('LCI', 'LCI'),
            ('NCO', 'NCO'),
        )
    
    @api.onchange('unit_amount','date_time')
    def onchange_unit_amount(self):
        if self.unit_amount and self.date_time:
            self.date_time_end = self.date_time + timedelta(hours=self.unit_amount)
        else:
            self.date_time_end = self.date_time

    employee_id = fields.Many2one(comodel_name="hr.employee", string="Empleado", default=lambda self: self.env.user.employee_id.id)
    project_id = fields.Many2one('project.project', 'Project', default=_default_project_id)
    ruta = fields.Boolean(string="Ruta")
    guardia = fields.Boolean(string="Guardia")
    vuelo_no_hlp = fields.Boolean(string="Vuelo NO Helipistas")
    vuelo_tipo_act_id = fields.Selection(_get_tipo_trabajo, 'Actividad vuelo')
    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request")
    unit_amount = fields.Float(string="Duración")
    sale_order = fields.Many2one(comodel_name='sale.order', string='Presupuesto', domain=[('flag_flight_part','=',True),('state','=','sale'),('tag_ids','=',False),('task_done','=',False)])
