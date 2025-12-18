# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResGroups(models.Model):
    _inherit = 'res.groups'

    # Campos adicionales para mejorar usabilidad
    color = fields.Integer(
        string='Color',
        default=0,
        help='Color index for visual identification (0-11)'
    )
    
    icon = fields.Char(
        string='Icon',
        help='FontAwesome icon class (e.g., fa-users, fa-cogs)'
    )
    
    description = fields.Html(
        string='Description',
        help='Detailed description of what this group allows'
    )
    
    group_category = fields.Char(
        string='Category',
        compute='_compute_group_category',
        store=True,
        help='Extracted from category_id or module name'
    )
    
    users_count = fields.Integer(
        string='Users Count',
        compute='_compute_users_count',
        store=False,
    )
    
    implied_count = fields.Integer(
        string='Implied Groups Count',
        compute='_compute_implied_count',
        store=False,
    )
    
    is_leulit_group = fields.Boolean(
        string='Is Leulit Group',
        compute='_compute_is_leulit_group',
        store=True,
        help='Group belongs to Leulit modules'
    )

    @api.depends('category_id', 'category_id.name', 'name')
    def _compute_group_category(self):
        """Extract category name for grouping"""
        for group in self:
            if group.category_id:
                group.group_category = group.category_id.name
            else:
                # Extract from name if no category
                group.group_category = 'Sin Categoría'

    @api.depends('users')
    def _compute_users_count(self):
        """Count active users in group"""
        for group in self:
            group.users_count = len(group.users.filtered(lambda u: u.active))

    @api.depends('implied_ids')
    def _compute_implied_count(self):
        """Count implied groups"""
        for group in self:
            group.implied_count = len(group.implied_ids)

    @api.depends('name', 'category_id', 'category_id.name')
    def _compute_is_leulit_group(self):
        """Identify Leulit custom groups"""
        for group in self:
            # Check if group belongs to any leulit module
            is_leulit = False
            if group.category_id:
                cat_name = group.category_id.name.lower()
                is_leulit = any(word in cat_name for word in [
                    'leulit', 'operaciones', 'escuela', 'taller', 
                    'camo', 'parte 145', 'calidad', 'seguridad'
                ])
            group.is_leulit_group = is_leulit

    def action_view_users(self):
        """Open users list filtered by this group"""
        self.ensure_one()
        return {
            'name': _('Users in %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'tree,form',
            'domain': [('groups_id', 'in', self.id)],
            'context': {'default_groups_id': [(4, self.id)]},
        }

    def action_view_implied_groups(self):
        """Open implied groups hierarchy"""
        self.ensure_one()
        return {
            'name': _('Implied Groups for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.groups',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.implied_ids.ids)],
        }
