# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_impersonating = fields.Boolean(
        string='Is Impersonating',
        compute='_compute_is_impersonating',
        help='True if this user is currently being impersonated'
    )
    
    can_impersonate = fields.Boolean(
        string='Can Impersonate',
        compute='_compute_can_impersonate',
        help='True if current user can impersonate this user'
    )

    @api.depends_context('uid')
    def _compute_is_impersonating(self):
        """Check if current session is impersonating"""
        impersonated_uid = self.env.context.get('impersonated_uid')
        for user in self:
            user.is_impersonating = bool(impersonated_uid and impersonated_uid == user.id)

    @api.depends_context('uid')
    def _compute_can_impersonate(self):
        """Check if current user has permission to impersonate"""
        can_impersonate = self.env.user.has_group('leulit_user_impersonate.group_impersonate_user')
        for user in self:
            # Cannot impersonate yourself or admin user (uid=1)
            user.can_impersonate = can_impersonate and user.id != self.env.uid and user.id != 1

    def action_impersonate_user(self):
        """Start impersonating this user"""
        self.ensure_one()
        
        # Security check
        if not self.env.user.has_group('leulit_user_impersonate.group_impersonate_user'):
            raise AccessError(_('You are not allowed to impersonate users.'))
        
        if self.id == self.env.uid:
            raise UserError(_('You cannot impersonate yourself.'))
        
        if self.id == 1:
            raise UserError(_('You cannot impersonate the administrator user.'))
        
        # Log the impersonation
        self.env['impersonate.log'].create({
            'original_user_id': self.env.uid,
            'impersonated_user_id': self.id,
            'start_date': fields.Datetime.now(),
        })
        
        _logger.info(
            'User %s (id=%s) started impersonating user %s (id=%s)',
            self.env.user.name, self.env.uid, self.name, self.id
        )
        
        # Return action to reload with impersonation context
        return {
            'type': 'ir.actions.client',
            'tag': 'start_impersonation',
            'params': {
                'user_id': self.id,
                'user_name': self.name,
            }
        }

    def action_stop_impersonation(self):
        """Stop impersonating and return to original user"""
        # This is called from the impersonated session
        # The actual stop is handled by the controller
        
        return {
            'type': 'ir.actions.client',
            'tag': 'stop_impersonation',
        }

    def action_view_menu_analysis(self):
        """View complete menu access analysis for this user"""
        self.ensure_one()
        
        # Generate analysis
        analysis_model = self.env['user.menu.analysis']
        analysis_model.generate_analysis(self.id)
        
        # Return action to show analysis
        return {
            'name': _('Menu Analysis: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'user.menu.analysis',
            'view_mode': 'tree,form',
            'domain': [('user_id', '=', self.id)],
            'context': {
                'default_user_id': self.id,
                'search_default_has_access': 1,
                'search_default_group_by_parent': 1,
            },
            'target': 'current',
        }
