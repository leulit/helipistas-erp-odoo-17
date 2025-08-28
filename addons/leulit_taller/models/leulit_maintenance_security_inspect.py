# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceSecurityInspect(models.Model):
    _name = "leulit.maintenance_security_inspect"


    @api.onchange('first_inspeccion_seguridad')
    def onchange_first_inspeccion_seguridad(self):
        if self.first_inspeccion_seguridad:
            self.first_user_inspeccion_seguridad = self.env.user.id
            self.first_datetime_inspeccion_seguridad = datetime.now()
        else:
            self.first_user_inspeccion_seguridad = False
            self.first_datetime_inspeccion_seguridad = False


    @api.onchange('second_inspeccion_seguridad')
    def onchange_second_inspeccion_seguridad(self):
        if self.second_inspeccion_seguridad:
            self.second_user_inspeccion_seguridad = self.env.user.id
            self.second_datetime_inspeccion_seguridad = datetime.now()
        else:
            self.second_user_inspeccion_seguridad = False
            self.second_datetime_inspeccion_seguridad = False


    name = fields.Char(string="Nombre")
    first_inspeccion_seguridad = fields.Boolean(string="Primer Inspección de seguridad")
    first_user_inspeccion_seguridad = fields.Many2one(comodel_name="res.users", string="Usuario Inspección seguridad")
    first_datetime_inspeccion_seguridad = fields.Datetime(string="Fecha y hora de la inspección de seguridad")
    second_inspeccion_seguridad = fields.Boolean(string="Segundo Inspección de seguridad")
    second_user_inspeccion_seguridad = fields.Many2one(comodel_name="res.users", string="Usuario Inspección seguridad")
    second_datetime_inspeccion_seguridad = fields.Datetime(string="Fecha y hora de la inspección de seguridad")
    task_id = fields.Many2one(comodel_name="project.task", string="Tarea")