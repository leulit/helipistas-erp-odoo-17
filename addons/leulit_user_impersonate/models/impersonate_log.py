# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class ImpersonateLog(models.Model):
    _name = 'impersonate.log'
    _description = 'User Impersonation Log'
    _order = 'start_date desc'
    _rec_name = 'original_user_id'

    original_user_id = fields.Many2one(
        'res.users',
        string='Original User',
        required=True,
        ondelete='cascade',
        help='User who initiated the impersonation'
    )
    
    impersonated_user_id = fields.Many2one(
        'res.users',
        string='Impersonated User',
        required=True,
        ondelete='cascade',
        help='User being impersonated'
    )
    
    start_date = fields.Datetime(
        string='Start Date',
        required=True,
        default=fields.Datetime.now,
        help='When the impersonation started'
    )
    
    end_date = fields.Datetime(
        string='End Date',
        help='When the impersonation ended'
    )
    
    duration = fields.Char(
        string='Duration',
        compute='_compute_duration',
        store=True,
        help='How long the impersonation lasted'
    )

    def _compute_duration(self):
        """Calculate duration of impersonation"""
        for log in self:
            if log.start_date and log.end_date:
                delta = log.end_date - log.start_date
                hours, remainder = divmod(int(delta.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                log.duration = f"{hours}h {minutes}m {seconds}s"
            else:
                log.duration = _('Active')
