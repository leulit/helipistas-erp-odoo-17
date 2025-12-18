# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class UserMenuAnalysis(models.TransientModel):
    _name = 'user.menu.analysis'
    _description = 'User Menu Access Analysis'
    _order = 'sequence, menu_id'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
    )
    
    menu_id = fields.Many2one(
        'ir.ui.menu',
        string='Menu',
        required=True,
        ondelete='cascade',
    )
    
    menu_name = fields.Char(
        string='Menu Name',
        related='menu_id.name',
        store=True,
    )
    
    parent_path = fields.Char(
        string='Menu Hierarchy',
        compute='_compute_parent_path',
        store=True,
    )
    
    has_access = fields.Boolean(
        string='Has Access',
        compute='_compute_access_info',
        store=True,
    )
    
    access_reason = fields.Text(
        string='Access Reason',
        compute='_compute_access_info',
        store=True,
        help='Why user has or does not have access',
    )
    
    groups_required = fields.Many2many(
        'res.groups',
        'user_menu_analysis_required_groups_rel',
        'analysis_id',
        'group_id',
        string='Groups Required',
        compute='_compute_access_info',
        store=True,
    )
    
    user_groups_matched = fields.Many2many(
        'res.groups',
        'user_menu_analysis_matched_groups_rel',
        'analysis_id',
        'group_id',
        string='User Groups (Matched)',
        compute='_compute_access_info',
        store=True,
        help='Groups that give access to this menu',
    )
    
    action_id = fields.Many2one(
        'ir.actions.actions',
        string='Action',
        related='menu_id.action',
        store=True,
    )
    
    action_type = fields.Char(
        string='Action Type',
        compute='_compute_action_info',
        store=True,
    )
    
    model_name = fields.Char(
        string='Model',
        compute='_compute_action_info',
        store=True,
    )
    
    view_types = fields.Char(
        string='View Types',
        compute='_compute_action_info',
        store=True,
        help='Available view types (tree, form, kanban, etc.)',
    )
    
    model_access_read = fields.Boolean(
        string='Read',
        compute='_compute_model_access',
        store=True,
    )
    
    model_access_write = fields.Boolean(
        string='Write',
        compute='_compute_model_access',
        store=True,
    )
    
    model_access_create = fields.Boolean(
        string='Create',
        compute='_compute_model_access',
        store=True,
    )
    
    model_access_unlink = fields.Boolean(
        string='Delete',
        compute='_compute_model_access',
        store=True,
    )
    
    menu_icon = fields.Char(
        string='Icon',
        related='menu_id.web_icon',
        store=True,
    )
    
    sequence = fields.Integer(
        string='Sequence',
        related='menu_id.sequence',
        store=True,
    )
    
    is_active = fields.Boolean(
        string='Menu Active',
        related='menu_id.active',
        store=True,
    )

    @api.depends('menu_id', 'menu_id.parent_id', 'menu_id.parent_id.parent_id')
    def _compute_parent_path(self):
        """Build complete menu hierarchy path"""
        for record in self:
            path_parts = []
            menu = record.menu_id
            while menu:
                path_parts.insert(0, menu.name)
                menu = menu.parent_id
            record.parent_path = ' / '.join(path_parts)

    @api.depends('menu_id', 'menu_id.groups_id', 'user_id', 'user_id.groups_id')
    def _compute_access_info(self):
        """Check if user has access and why"""
        for record in self:
            menu_groups = record.menu_id.groups_id
            user_groups = record.user_id.groups_id
            
            record.groups_required = menu_groups
            
            if not menu_groups:
                # No groups required = everyone has access
                record.has_access = True
                record.access_reason = _('Public menu (no groups required)')
                record.user_groups_matched = self.env['res.groups']
            else:
                # Check if user has any of the required groups
                matched_groups = user_groups & menu_groups
                record.user_groups_matched = matched_groups
                
                if matched_groups:
                    record.has_access = True
                    group_names = ', '.join(matched_groups.mapped('name'))
                    record.access_reason = _('Access via groups: %s') % group_names
                else:
                    record.has_access = False
                    required_names = ', '.join(menu_groups.mapped('name'))
                    record.access_reason = _('Missing required groups: %s') % required_names

    @api.depends('action_id')
    def _compute_action_info(self):
        """Get action details: type, model, view types"""
        for record in self:
            if not record.action_id:
                record.action_type = _('No action')
                record.model_name = ''
                record.view_types = ''
                continue
            
            action = record.action_id
            record.action_type = action._name
            
            # Try to get model from action
            if hasattr(action, 'res_model'):
                record.model_name = action.res_model
            else:
                record.model_name = ''
            
            # Try to get view types from action
            if hasattr(action, 'view_mode'):
                record.view_types = action.view_mode
            else:
                record.view_types = ''

    @api.depends('model_name', 'user_id')
    def _compute_model_access(self):
        """Check CRUD permissions on the model"""
        for record in self:
            if not record.model_name:
                record.model_access_read = False
                record.model_access_write = False
                record.model_access_create = False
                record.model_access_unlink = False
                continue
            
            try:
                # Check access rights as the target user
                model = self.env[record.model_name].with_user(record.user_id)
                record.model_access_read = model.check_access_rights('read', raise_exception=False)
                record.model_access_write = model.check_access_rights('write', raise_exception=False)
                record.model_access_create = model.check_access_rights('create', raise_exception=False)
                record.model_access_unlink = model.check_access_rights('unlink', raise_exception=False)
            except Exception as e:
                _logger.warning('Error checking access for model %s: %s', record.model_name, str(e))
                record.model_access_read = False
                record.model_access_write = False
                record.model_access_create = False
                record.model_access_unlink = False

    @api.model
    def generate_analysis(self, user_id):
        """Generate complete menu analysis for a user"""
        # Clean previous analysis
        self.search([('user_id', '=', user_id)]).unlink()
        
        # Get all menus
        all_menus = self.env['ir.ui.menu'].search([])
        
        # Create analysis records
        records = []
        for menu in all_menus:
            records.append({
                'user_id': user_id,
                'menu_id': menu.id,
            })
        
        created = self.create(records)
        
        _logger.info('Generated menu analysis for user %s: %s menus analyzed', user_id, len(created))
        
        return created
