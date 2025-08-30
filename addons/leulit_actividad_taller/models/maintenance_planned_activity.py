# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class MiantenancePlannedactivity(models.Model):
    _name = "maintenance.planned.activity"
    _inherit = "maintenance.planned.activity"


    tipos_actividad = fields.Many2many('leulit.tipo_actividad_mecanico','rel_tipo_actividad_planned_activity','planned_activity_id','tipo_actividad_id','Tipo actividad mecánico')