from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ChecklistTareasSensiblesSeguridad(models.Model):
    _name = 'leulit.checklist_tareas_sensibles_seguridad'
    _description = 'Checklist de Tareas Sensibles para la Seguridad'
    _rec_name = "name"

    name = fields.Char(string="Nombre")
    tareas = fields.One2many(comodel_name="leulit.tarea_sensible_seguridad", inverse_name="checklist_id", string="Tareas")