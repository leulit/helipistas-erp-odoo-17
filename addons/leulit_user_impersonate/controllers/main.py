# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class ImpersonateController(http.Controller):

    @http.route('/web/impersonate/start', type='json', auth='user')
    def start_impersonation(self, user_id):
        """
        Start impersonating a user by storing original user in session
        and switching to the target user
        """
        # Security check
        if not request.env.user.has_group('leulit_user_impersonate.group_impersonate_user'):
            raise AccessError('You are not allowed to impersonate users.')
        
        # Cannot impersonate yourself
        if user_id == request.env.uid:
            return {'error': 'Cannot impersonate yourself'}
        
        # Cannot impersonate admin
        if user_id == 1:
            return {'error': 'Cannot impersonate administrator'}
        
        # Verify target user exists
        target_user = request.env['res.users'].sudo().browse(user_id)
        if not target_user.exists():
            return {'error': 'User not found'}
        
        # Store original user in session
        original_uid = request.session.uid
        request.session['impersonate_original_uid'] = original_uid
        request.session['impersonate_target_uid'] = user_id
        
        # Switch to target user
        request.session.uid = user_id
        request.env = request.env(user=user_id)
        
        _logger.info(
            'User %s started impersonating user %s (uid=%s)',
            original_uid, target_user.name, user_id
        )
        
        return {
            'success': True,
            'impersonated_user': {
                'id': user_id,
                'name': target_user.name,
            },
            'original_user': {
                'id': original_uid,
                'name': request.env['res.users'].sudo().browse(original_uid).name,
            }
        }

    @http.route('/web/impersonate/stop', type='json', auth='user')
    def stop_impersonation(self):
        """
        Stop impersonating and return to original user
        """
        original_uid = request.session.get('impersonate_original_uid')
        target_uid = request.session.get('impersonate_target_uid')
        
        if not original_uid or not target_uid:
            return {'error': 'No active impersonation session'}
        
        # Update log end date
        log = request.env['impersonate.log'].sudo().search([
            ('original_user_id', '=', original_uid),
            ('impersonated_user_id', '=', target_uid),
            ('end_date', '=', False),
        ], limit=1)
        
        if log:
            log.write({'end_date': http.request.env.context.get('tz')})
        
        # Restore original user
        request.session.uid = original_uid
        request.env = request.env(user=original_uid)
        
        # Clear impersonation session data
        request.session.pop('impersonate_original_uid', None)
        request.session.pop('impersonate_target_uid', None)
        
        _logger.info(
            'User %s stopped impersonating user %s',
            original_uid, target_uid
        )
        
        return {
            'success': True,
            'original_user_id': original_uid,
        }

    @http.route('/web/impersonate/status', type='json', auth='user')
    def get_impersonation_status(self):
        """
        Check if current session is impersonating
        """
        original_uid = request.session.get('impersonate_original_uid')
        target_uid = request.session.get('impersonate_target_uid')
        
        if original_uid and target_uid:
            original_user = request.env['res.users'].sudo().browse(original_uid)
            target_user = request.env['res.users'].sudo().browse(target_uid)
            
            return {
                'is_impersonating': True,
                'original_user': {
                    'id': original_uid,
                    'name': original_user.name,
                },
                'impersonated_user': {
                    'id': target_uid,
                    'name': target_user.name,
                }
            }
        
        return {'is_impersonating': False}
