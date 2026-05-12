# -*- encoding: utf-8 -*-
from odoo import models, fields


class ProjectProject(models.Model):
    _inherit = 'project.project'

    privacy_visibility = fields.Selection(default='followers')
