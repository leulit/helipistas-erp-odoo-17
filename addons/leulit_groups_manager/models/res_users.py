# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Campos computados para mejor visualización
    groups_count = fields.Integer(
        string='Groups Count',
        compute='_compute_groups_count',
        store=False,
    )
    
    leulit_groups_count = fields.Integer(
        string='Leulit Groups',
        compute='_compute_leulit_groups_count',
        store=False,
    )
    
    groups_by_category = fields.Html(
        string='Groups by Category',
        compute='_compute_groups_by_category',
        store=False,
        help='Formatted display of groups organized by category'
    )

    @api.depends('groups_id')
    def _compute_groups_count(self):
        """Count total groups"""
        for user in self:
            user.groups_count = len(user.groups_id)

    @api.depends('groups_id', 'groups_id.is_leulit_group')
    def _compute_leulit_groups_count(self):
        """Count Leulit-specific groups"""
        for user in self:
            leulit_groups = user.groups_id.filtered(lambda g: g.is_leulit_group)
            user.leulit_groups_count = len(leulit_groups)

    @api.depends('groups_id', 'groups_id.category_id', 'groups_id.group_category', 
                 'groups_id.is_leulit_group', 'groups_id.icon', 'groups_id.name')
    def _compute_groups_by_category(self):
        """Generate HTML display of groups organized by category"""
        for user in self:
            if not user.groups_id:
                user.groups_by_category = '<p class="text-muted">No groups assigned</p>'
                continue
            
            # Group by category
            categories = {}
            for group in user.groups_id.sorted(lambda g: g.full_name):
                cat_name = group.group_category or 'Sin Categoría'
                if cat_name not in categories:
                    categories[cat_name] = []
                categories[cat_name].append(group)
            
            # Build HTML
            html_parts = ['<div class="groups_by_category">']
            for cat_name in sorted(categories.keys()):
                groups = categories[cat_name]
                html_parts.append(f'<div class="category_section">')
                html_parts.append(f'<h5 class="text-primary">{cat_name}</h5>')
                html_parts.append('<ul class="list-unstyled">')
                for group in groups:
                    badge_class = 'badge-success' if group.is_leulit_group else 'badge-secondary'
                    icon = group.icon or 'fa-tag'
                    html_parts.append(
                        f'<li><i class="fa {icon}"></i> '
                        f'<span class="badge {badge_class}">{group.name}</span></li>'
                    )
                html_parts.append('</ul></div>')
            html_parts.append('</div>')
            
            user.groups_by_category = ''.join(html_parts)

    def action_open_groups_matrix(self):
        """Open visual matrix for group assignment"""
        self.ensure_one()
        return {
            'name': _('Manage Groups for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('leulit_groups_manager.view_users_form_groups_matrix').id,
            'target': 'new',
        }

    def action_view_group_analysis(self):
        """Show detailed analysis of user's groups and permissions"""
        self.ensure_one()
        
        # Collect all groups (direct + implied)
        all_groups = self.groups_id
        implied_groups = self.env['res.groups']
        for group in self.groups_id:
            implied_groups |= group.implied_ids
        
        return {
            'name': _('Group Analysis for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.groups',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', (all_groups | implied_groups).ids)],
            'context': {
                'user_id': self.id,
                'default_color': 3,
            },
        }
