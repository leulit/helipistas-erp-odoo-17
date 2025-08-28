# -*- encoding: utf-8 -*-
from odoo.addons.leulit import utilitylib
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta

import logging
_logger = logging.getLogger(__name__)


class LeulitOperacionesPerformance(models.Model):
    _name           = "leulit.operaciones_performance"
    _description    = "leulit_operaciones_performance"


    name = fields.Char(string='Nombre')