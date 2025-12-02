from datetime import datetime, timedelta
from odoo import fields, models


class WizardCreateEventFromTask(models.TransientModel):
    _name = "leulit.wizard_create_event_from_task"

    def create_event_from_task(self):
        self.ensure_one()
        task = self.task_id
        event_vals = {
            "name": task.name,
            "start": task.date_deadline or datetime.now(),
            "stop": (task.date_deadline + timedelta(hours=1)) if task.date_deadline else (datetime.now() + timedelta(hours=1)),
            "description": task.description or "",
        }
        event = self.env["calendar.event"].create(event_vals)
        task.event_id = event.id
        return {"type": "ir.actions.act_window_close"}
    

    task_id = fields.Many2one("project.task", "Tarea", required=True)
    type_event = fields.Many2one(comodel_name='leulit.tipo_planificacion', string='Tipo', required=True)
    duration = fields.Float(string='Duración (horas)', required=True, default=1.0)
    start = fields.Datetime(string='Iniciar', required=True)