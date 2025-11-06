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


    def action_switch(self):
        super(HrTimesheetSwitch, self).action_switch()
            
        return {
            "type": "ir.actions.act_multi",
            "actions": [
                {"type": "ir.actions.act_window_close"},
                {"type": "ir.actions.act_view_reload"},
            ],
        }


    def _default_project_id(self):
        return self.env['project.project'].search([('name','=','Internal'),('company_id','=',self.env.company.id)])


    employee_id = fields.Many2one(comodel_name="hr.employee", string="Empleado", default=lambda self: self.env.user.employee_id.id)
    until_date = fields.Datetime(string="Hasta")
    recurrency = fields.Boolean(string="Recurrente")
    project_id = fields.Many2one('project.project', 'Project', default=_default_project_id)