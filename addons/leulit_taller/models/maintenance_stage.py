from datetime import date, datetime, timedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class MaintenanceStage(models.Model):
    _inherit = 'maintenance.stage'

    accepted = fields.Boolean('Solicitud aceptada')
    flight = fields.Boolean('En vuelo')