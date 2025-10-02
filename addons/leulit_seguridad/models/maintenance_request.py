# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class MaintenanceRequest(models.Model):
    _name = "maintenance.request"
    _inherit = "maintenance.request"


    anomalia_ids = fields.One2many(comodel_name="leulit.anomalia", inverse_name="maintenance_request_id", string="Anomalias")



    def open_wizard_asign_anomalia(self):
        self.ensure_one()
        view = self.env.ref('leulit_seguridad.leulit_20230704_1748_form',raise_if_not_found=False)

        context = {
            'default_rel_maintenance_request': self.id,
            'default_helicoptero': self.helicoptero.id
        }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Anomalía',
            'res_model': 'leulit.wizard_asign_anomalia',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'context': context,
        }