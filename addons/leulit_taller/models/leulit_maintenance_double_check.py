# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceDoubleCheck(models.Model):
    _name = "leulit.maintenance_double_check"


    @api.onchange('first_doble_check')
    def onchange_first_doble_check(self):
        if self.first_doble_check:
            self.first_user_doble_check = self.env.user.id
            self.first_datetime_doble_check = datetime.now()
        else:
            self.first_user_doble_check = False
            self.first_datetime_doble_check = False


    @api.onchange('second_doble_check')
    def onchange_second_doble_check(self):
        if self.second_doble_check:
            self.second_user_doble_check = self.env.user.id
            self.second_datetime_doble_check = datetime.now()
        else:
            self.second_user_doble_check = False
            self.second_datetime_doble_check = False
    

    name = fields.Char(string="Nombre")
    first_doble_check = fields.Boolean(string="Primer Doble check")
    first_user_doble_check = fields.Many2one(comodel_name="res.users", string="Usuario doble check")
    first_datetime_doble_check = fields.Datetime(string="Fecha y hora del doble check")
    second_doble_check = fields.Boolean(string="Segundo Doble check")
    second_user_doble_check = fields.Many2one(comodel_name="res.users", string="Usuario doble check")
    second_datetime_doble_check = fields.Datetime(string="Fecha y hora del doble check")
    task_id = fields.Many2one(comodel_name="project.task", string="Tarea")