
from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)



class LeulitLimitacionesAeronavegabilidad(models.Model):
    _name = "leulit.limitaciones_aeronavegabilidad"

    name = fields.Char(string="Nombre")
    manual_id = fields.Many2one(comodel_name="leulit.maintenance_manual", string="Manual")