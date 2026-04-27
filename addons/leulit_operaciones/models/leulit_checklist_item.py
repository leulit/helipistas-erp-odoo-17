# -*- encoding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class leulit_checklist_item(models.Model):
    _inherit = "leulit.checklist_item"

    def checklist_item_doit(self):
        for item in self:
            if item.requiere_parte_vuelo:
                uid = item.checklist_id.realizado_por.id
                fecha = item.checklist_id.fecha_doit
                pilotos = self.env['leulit.piloto'].search([('user_ids', '=', uid)])
                if not pilotos:
                    raise UserError(_("El autor de la checklist no tiene ningún piloto asociado."))
                vuelos = self.env['leulit.vuelo'].search([
                    ('piloto_id', 'in', pilotos.ids),
                    ('fechavuelo', '=', fecha),
                    ('estado', '!=', 'cancelado'),
                ], limit=1)
                if not vuelos:
                    raise UserError(_(
                        "Para marcar este punto como realizado debe existir un parte de vuelo "
                        "del día %s con el autor de la checklist como piloto."
                    ) % fecha)
        return super().checklist_item_doit()
