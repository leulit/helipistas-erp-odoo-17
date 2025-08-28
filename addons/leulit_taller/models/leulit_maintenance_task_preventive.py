# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class LeulitMaintenanceTaskPreventive(models.Model):
    _name = "leulit.maintenance_task_preventive"
    _rec_name = "descripcion"

    descripcion = fields.Char(string="Descripción")
    referencia = fields.Char(string="Referencia")
    planned_activity_ids = fields.One2many(comodel_name="maintenance.planned.activity", inverse_name="tarea_preventiva_id", string="Tareas en plan de mantenimiento")