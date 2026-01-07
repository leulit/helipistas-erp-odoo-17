# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class MenuListWizard(models.TransientModel):
    _name = 'menu.list.wizard'
    _description = 'Menu List Wizard with Access Colors'

    user_id = fields.Many2one('res.users', string='User', required=True)
    menu_list_html = fields.Html(string='Menu List', compute='_compute_menu_list_html')

    @api.depends('user_id')
    def _compute_menu_list_html(self):
        """Generate HTML list of all menus with color coding"""
        for wizard in self:
            if not wizard.user_id:
                wizard.menu_list_html = '<p class="text-muted">Please select a user</p>'
                continue
            
            # Get all user's groups (including implied)
            all_groups = wizard.user_id.groups_id
            for group in wizard.user_id.groups_id:
                all_groups |= group.implied_ids
            
            html = ['<div style="font-family: Arial, sans-serif;">']
            
            # Legend
            html.append('<div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px; margin-bottom: 15px;">')
            html.append('<h4 style="margin-top: 0;">Leyenda:</h4>')
            html.append('<p style="margin: 5px 0;"><span style="color: #28a745; font-size: 20px;">●</span> <strong>Verde</strong> = Usuario tiene acceso</p>')
            html.append('<p style="margin: 5px 0;"><span style="color: #dc3545; font-size: 20px;">●</span> <strong>Rojo</strong> = Usuario NO tiene acceso</p>')
            html.append('</div>')
            
            # Get all root menus (no parent)
            root_menus = self.env['ir.ui.menu'].search([('parent_id', '=', False)], order='sequence, name')
            
            html.append('<div style="padding: 10px;">')
            
            for root_menu in root_menus:
                wizard._build_menu_tree_html(html, root_menu, all_groups, level=0)
            
            html.append('</div>')
            html.append('</div>')
            
            wizard.menu_list_html = ''.join(html)

    def _check_menu_access(self, menu, all_groups):
        """Check if user has access to a menu"""
        menu_groups = menu.groups_id
        if not menu_groups:
            return True  # No groups = accessible to all
        return bool(all_groups & menu_groups)

    def _build_menu_tree_html(self, html, menu, all_groups, level=0):
        """Recursively build menu tree with colors"""
        has_access = self._check_menu_access(menu, all_groups)
        color = '#28a745' if has_access else '#dc3545'
        icon = '●' if has_access else '●'
        
        # Indentation
        indent = '&nbsp;' * (level * 4)
        
        # Menu name with color
        html.append(f'<div style="margin: 3px 0; padding: 2px 0;">')
        html.append(f'{indent}<span style="color: {color}; font-size: 16px;">{icon}</span> ')
        html.append(f'<span style="color: {color}; font-weight: {"bold" if level == 0 else "normal"};">{menu.name}</span>')
        
        # Show groups if any
        if menu.groups_id:
            groups_names = ', '.join(menu.groups_id.mapped('name')[:3])
            if len(menu.groups_id) > 3:
                groups_names += f' (+{len(menu.groups_id) - 3} more)'
            html.append(f' <small style="color: #6c757d;">({groups_names})</small>')
        
        html.append('</div>')
        
        # Recursively process children
        child_menus = self.env['ir.ui.menu'].search([('parent_id', '=', menu.id)], order='sequence, name')
        for child_menu in child_menus:
            self._build_menu_tree_html(html, child_menu, all_groups, level + 1)
