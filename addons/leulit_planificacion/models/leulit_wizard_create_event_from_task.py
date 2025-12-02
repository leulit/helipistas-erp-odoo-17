from datetime import datetime, timedelta
from odoo import fields, models


class WizardCreateEventFromTask(models.TransientModel):
    _name = "leulit.wizard_create_event_from_task"

    def create_event_from_task(self):
        self.ensure_one()
        task = self.task_id
        partners = task.user_ids.mapped('partner_id').ids
        event_vals = {
            "name": task.name,
            "start": self.start,
            "stop": self.start + timedelta(hours=self.duration),
            "duration": self.duration,
            "type_event": self.type_event.id,
            "description": task.description or "",
            "partner_ids": [(6, 0, partners)],
            "user_id": self.env.user.id,
            "task_id": task.id,
        }
        event = self.env["calendar.event"].create(event_vals)
        task.event_ids = [(4, event.id)]
        return {"type": "ir.actions.act_window_close"}
    

    task_id = fields.Many2one("project.task", "Tarea", required=True)
    type_event = fields.Many2one(comodel_name='leulit.tipo_planificacion', string='Tipo')
    duration = fields.Float(string='Duración (horas)', default=1.0)
    start = fields.Datetime(string='Iniciar')