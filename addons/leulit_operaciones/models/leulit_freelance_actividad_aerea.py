# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)


class leulitFreelanceActividadAerea(models.Model):
    _name           = "leulit.freelance_actividad_aerea"
    _description    = "leulit_freelance_actividad_aerea"
    _order          = "date desc"

    def print_certificate_actividad_aerea(self):
        """Prints the certificate of the activity."""
        self.ensure_one()
        return self.env.ref('leulit_operaciones.leulit_20250318_1638_report').report_action(self)

    user = fields.Many2one(comodel_name="res.users", string="Usuario", required=True)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    text = fields.Text(string="Texto")
    company = fields.Many2one(comodel_name="res.company", string="Compañía", default=1)
