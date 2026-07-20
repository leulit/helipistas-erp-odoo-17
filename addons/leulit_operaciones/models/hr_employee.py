# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    plus_festivo_nacional = fields.Float(string="Plus Festivo/Nacional")
