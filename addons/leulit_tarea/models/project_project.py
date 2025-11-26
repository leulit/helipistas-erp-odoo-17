# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, api, models
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = "project.project"

    def action_close_all_tasks(self):
        """
        Cierra todas las tareas asociadas al proyecto, cambiando su etapa a 'Finalizado' o 'Hecho'.
        Busca la etapa por nombre para mayor flexibilidad.
        """
        self.ensure_one()
        # Buscar etapa por nombre (case-insensitive)
        stage_done = self.env['project.task.type'].search([
            ('name', 'ilike', 'finalizado')
        ], limit=1)
        if not stage_done:
            stage_done = self.env['project.task.type'].search([
                ('name', 'ilike', 'hecho')
            ], limit=1)
        if not stage_done:
            _logger.warning("No se encontró ninguna etapa de tarea llamada 'Finalizado' o 'Hecho'. No se cerrarán tareas.")
            return
        tasks_to_close = self.task_ids.filtered(lambda t: t.stage_id != stage_done)
        if not tasks_to_close:
            _logger.info(f"No hay tareas abiertas para cerrar en el proyecto {self.display_name}.")
            return
        tasks_to_close.write({'stage_id': stage_done.id})
        _logger.info(f"Se han cerrado {len(tasks_to_close)} tareas del proyecto {self.display_name}.")
