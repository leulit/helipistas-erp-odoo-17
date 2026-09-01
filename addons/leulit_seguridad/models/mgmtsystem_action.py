# -*- encoding: utf-8 -*-
from odoo import fields, models


class MgmtsystemAction(models.Model):
    _inherit = "mgmtsystem.action"

    risk_type_id = fields.Many2one("mgmtsystem.hazard.risk.type", string="Peligro")

    def write(self, vals):
        # El módulo base solo rellena date_closed la primera vez que la
        # acción entra en un stage "is_ending" (Cerrado o Cancelado) y ya no
        # lo toca después. Aquí lo tratamos como lo que es, una fecha de
        # cierre real: solo tiene sentido si el stage actual es "Cerrado", se
        # actualiza cada vez que se llega a él (incluida una corrección desde
        # Cancelado) y se borra en cualquier otro caso (Cancelado, reabierta,
        # etc.).
        estados_previos = {a.id: a.stage_id.id for a in self} if "stage_id" in vals else {}
        res = super().write(vals)
        if "stage_id" in vals:
            stage_close = self.env.ref(
                "mgmtsystem_action.stage_close", raise_if_not_found=False
            )
            cambiadas = self.filtered(
                lambda a: a.stage_id.id != estados_previos.get(a.id)
            )
            cerradas = cambiadas.filtered(lambda a: stage_close and a.stage_id == stage_close)
            resto = (cambiadas - cerradas).filtered("date_closed")
            if cerradas:
                cerradas.write({"date_closed": fields.Datetime.now()})
            if resto:
                resto.write({"date_closed": False})
        return res
