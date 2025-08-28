# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class LeulitCertificacion(models.Model):
    _name = "leulit.certificacion"
    _rec_name = "name"


    name = fields.Char(string="Nombre")