# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class MenuAccessDiagnosisWizard(models.TransientModel):
    _name = 'menu.access.diagnosis.wizard'
    _description = 'Menu Access Diagnosis Wizard'

    user_id = fields.Many2one('res.users', string='User', required=True)
    menu_id = fields.Many2one('ir.ui.menu', string='Menu', required=True)
    diagnosis_result = fields.Html(string='Diagnosis Result', readonly=True)

    @api.onchange('user_id', 'menu_id')
    def _onchange_diagnose(self):
        """Automatically diagnose when user or menu changes"""
        if self.user_id and self.menu_id:
            self.diagnosis_result = self._perform_diagnosis()

    def action_diagnose(self):
        """Perform diagnosis and show result"""
        self.ensure_one()
        self.diagnosis_result = self._perform_diagnosis()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _check_menu_access(self, menu, all_user_groups):
        """Check if user has access to a specific menu"""
        menu_groups = menu.groups_id
        if not menu_groups:
            return True  # No groups = accessible to all
        return bool(all_user_groups & menu_groups)

    def _get_colored_hierarchy(self, all_user_groups):
        """Build colored hierarchy string (e.g., CRM/Ventas with colors)"""
        # Build menu chain from current to root
        chain = []
        current = self.menu_id
        while current:
            chain.append(current)
            current = current.parent_id
        
        # Reverse to show from root to current
        chain.reverse()
        
        # Build colored HTML
        parts = []
        for menu in chain:
            has_access = self._check_menu_access(menu, all_user_groups)
            if has_access:
                parts.append(f'<span style="color: #28a745; font-weight: bold;">{menu.name}</span>')
            else:
                parts.append(f'<span style="color: #dc3545; font-weight: bold;">{menu.name}</span>')
        
        return ' / '.join(parts)

    def _perform_diagnosis(self):
        """Perform the actual diagnosis"""
        if not self.user_id or not self.menu_id:
            return '<p class="text-muted">Please select both user and menu</p>'

        html = ['<div class="menu_diagnosis" style="font-family: Arial, sans-serif;">']
        
        # Get user groups early
        user_groups = self.user_id.groups_id
        implied_groups = self.env['res.groups']
        for group in user_groups:
            implied_groups |= group.implied_ids
        all_user_groups = user_groups | implied_groups
        
        # Menu hierarchy with colors
        html.append('<h4>Menu Hierarchy (with Access Status):</h4>')
        html.append(f'<p style="font-size: 16px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">')
        html.append(self._get_colored_hierarchy(all_user_groups))
        html.append('</p>')
        html.append('<p style="margin-top: 5px;"><small>')
        html.append('<span style="color: #28a745;">■</span> Green = User has access | ')
        html.append('<span style="color: #dc3545;">■</span> Red = User does NOT have access')
        html.append('</small></p>')
        
        # Menu info
        html.append(f'<hr/>')
        html.append(f'<h4>Menu Details: {self.menu_id.name}</h4>')
        html.append(f'<p><strong>Full Path:</strong> {self.menu_id.complete_name}</p>')
        html.append(f'<p><strong>ID:</strong> {self.menu_id.id}</p>')
        html.append(f'<p><strong>XML ID:</strong> {self.menu_id.get_external_id().get(self.menu_id.id, "N/A")}</p>')
        
        # Check if menu is active
        if not self.menu_id.active:
            html.append('<div class="alert alert-danger"><i class="fa fa-times-circle"></i> <strong>Menu is INACTIVE</strong></div>')
        
        # Get menu groups
        menu_groups = self.menu_id.groups_id
        html.append(f'<h5>Groups required for this menu ({len(menu_groups)}):</h5>')
        
        if not menu_groups:
            html.append('<div class="alert alert-info"><i class="fa fa-info-circle"></i> This menu has <strong>NO GROUPS</strong> assigned (visible to all users)</div>')
        else:
            html.append('<ul>')
            for group in menu_groups:
                html.append(f'<li><strong>{group.full_name}</strong> (ID: {group.id})</li>')
            html.append('</ul>')
        
        # Get user groups
        html.append(f'<h5>User\'s Direct Groups ({len(user_groups)}):</h5>')
        html.append('<ul>')
        for group in user_groups:
            html.append(f'<li>{group.full_name}</li>')
        html.append('</ul>')
        
        # Get implied groups
        if implied_groups:
            html.append(f'<h5>Implied Groups ({len(implied_groups)}):</h5>')
            html.append('<ul>')
            for group in implied_groups:
                html.append(f'<li>{group.full_name}</li>')
            html.append('</ul>')
        
        # Check access
        html.append('<hr/>')
        html.append('<h4>Access Analysis:</h4>')
        
        if not menu_groups:
            html.append('<div class="alert alert-success"><i class="fa fa-check-circle"></i> <strong>USER HAS ACCESS</strong> (menu has no group restrictions)</div>')
        else:
            # Check intersection
            matching_groups = all_user_groups & menu_groups
            
            if matching_groups:
                html.append('<div class="alert alert-success"><i class="fa fa-check-circle"></i> <strong>USER HAS ACCESS to this menu</strong></div>')
                html.append('<p>User has the following required groups:</p>')
                html.append('<ul>')
                for group in matching_groups:
                    html.append(f'<li class="text-success"><strong>{group.full_name}</strong></li>')
                html.append('</ul>')
            else:
                html.append('<div class="alert alert-danger"><i class="fa fa-times-circle"></i> <strong>USER DOES NOT HAVE ACCESS to this menu</strong></div>')
                html.append('<p class="text-danger">User does not have any of the required groups.</p>')
                html.append('<p><strong>Missing groups:</strong></p>')
                html.append('<ul>')
                for group in menu_groups:
                    html.append(f'<li class="text-danger">{group.full_name} (ID: {group.id})</li>')
                html.append('</ul>')
                
                # Suggest solution
                html.append('<hr/>')
                html.append('<h5>Solution:</h5>')
                html.append('<p>To grant access to this menu, add one of the following groups to the user:</p>')
                html.append('<ul>')
                for group in menu_groups:
                    html.append(f'<li><a href="/web#id={group.id}&model=res.groups&view_type=form" target="_blank">{group.full_name}</a></li>')
                html.append('</ul>')
        
        # Check parent menus in detail
        if self.menu_id.parent_id:
            html.append('<hr/>')
            html.append('<h4 style="color: #dc3545;">⚠️ Critical: Parent Menu Access</h4>')
            html.append('<p><strong>Even if the user has access to this menu, ALL parent menus must also be accessible!</strong></p>')
            
            # Build parent chain
            parent_chain = []
            parent = self.menu_id.parent_id
            while parent:
                parent_chain.append(parent)
                parent = parent.parent_id
            parent_chain.reverse()
            
            html.append('<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">')
            html.append('<tr style="background-color: #f8f9fa;">')
            html.append('<th style="padding: 8px; border: 1px solid #dee2e6; text-align: left;">Menu</th>')
            html.append('<th style="padding: 8px; border: 1px solid #dee2e6; text-align: center;">Access</th>')
            html.append('<th style="padding: 8px; border: 1px solid #dee2e6; text-align: left;">Required Groups</th>')
            html.append('</tr>')
            
            all_parents_accessible = True
            for parent_menu in parent_chain:
                has_access = self._check_menu_access(parent_menu, all_user_groups)
                if not has_access:
                    all_parents_accessible = False
                
                access_icon = '✓' if has_access else '✗'
                access_color = '#28a745' if has_access else '#dc3545'
                row_bg = '#d4edda' if has_access else '#f8d7da'
                
                html.append(f'<tr style="background-color: {row_bg};">')
                html.append(f'<td style="padding: 8px; border: 1px solid #dee2e6;"><strong>{parent_menu.complete_name}</strong></td>')
                html.append(f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center; color: {access_color}; font-size: 18px;">{access_icon}</td>')
                
                parent_groups = parent_menu.groups_id
                if not parent_groups:
                    html.append('<td style="padding: 8px; border: 1px solid #dee2e6;"><em>No groups (accessible to all)</em></td>')
                else:
                    groups_list = ', '.join([g.name for g in parent_groups])
                    html.append(f'<td style="padding: 8px; border: 1px solid #dee2e6;">{groups_list}</td>')
                html.append('</tr>')
            
            html.append('</table>')
            
            # Summary
            if not all_parents_accessible:
                html.append('<div class="alert alert-danger" style="margin-top: 15px;">')
                html.append('<i class="fa fa-exclamation-triangle"></i> <strong>PROBLEM FOUND:</strong> ')
                html.append('User does NOT have access to one or more parent menus. ')
                html.append('This is why the menu is not visible in the UI, even if the user has access to the menu itself.')
                html.append('</div>')
            else:
                html.append('<div class="alert alert-success" style="margin-top: 15px;">')
                html.append('<i class="fa fa-check-circle"></i> <strong>All parent menus are accessible.</strong>')
                html.append('</div>')
        
        html.append('</div>')
        return ''.join(html)
