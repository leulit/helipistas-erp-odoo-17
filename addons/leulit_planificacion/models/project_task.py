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
    event_ids = fields.One2many("calendar.event", "task_id", "Eventos")

    def create_event_from_task(self):
        # Abre un wizard para crear un evento de calendario a partir de la tarea
        self.ensure_one()
        wizard = self.env["leulit.wizard_create_event_from_task"].create(
            {
                "task_id": self.id,
                "start": self.date_deadline or datetime.now(),
            }
        )
        return {
            "name": "Crear evento de calendario",
            "type": "ir.actions.act_window",
            "res_model": "leulit.wizard_create_event_from_task",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }