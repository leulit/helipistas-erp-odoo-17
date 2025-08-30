# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class LeulitJobCardItem(models.Model):
    _inherit = "leulit.job_card_item"

    tipos_actividad = fields.Many2many('leulit.tipo_actividad_mecanico','rel_tipo_job_card_item','job_card_item_id','tipo_actividad_id','Tipo actividad mecánico')