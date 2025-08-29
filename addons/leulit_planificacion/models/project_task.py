# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, api, models
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task"]

    reunion_id = fields.Many2one("leulit.reunion", "Reunion")