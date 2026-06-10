# -*- encoding: utf-8 -*-
from odoo import models, fields


class leulit_helicoptero(models.Model):
    _inherit = "leulit.helicoptero"

    def _compute_can_edit(self):
        can = self.user_has_groups(
            'leulit.RBase_hide,leulit.ROperaciones_gestor,leulit.RTaller_base,leulit.RCAMO_base'
            ',leulit_planificacion.RPlanificacion_planner'
        )
        for rec in self:
            rec.can_edit = can
