# -*- encoding: utf-8 -*-
from odoo import models, fields


class ProjectProject(models.Model):
    _inherit = 'project.project'

    privacy_visibility = fields.Selection(default='followers')

    is_developer_user = fields.Boolean(compute='_compute_is_developer_user')

    def _compute_is_developer_user(self):
        is_dev = self.env.user.has_group('leulit.RolIT_developer')
        for record in self:
            record.is_developer_user = is_dev
