# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, Command, fields, models, _
from odoo.exceptions import AccessError
from odoo.tools import format_amount
from odoo.tools.sql import column_exists, create_column


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _timesheet_create_task_prepare_values(self, project):
        self.ensure_one()
        allocated_hours = 0.0
        if self.product_id.service_type not in ['milestones', 'manual']:
            allocated_hours = self._convert_qty_company_hours(self.company_id)
        sale_line_name_parts = self.name.split('\n')
        title = sale_line_name_parts[0] or self.product_id.name
        description = self.order_id.note.split('----------')[0] if self.order_id.note else ''
        return {
            'name': title if project.sale_line_id else '%s - %s' % (self.order_id.name or '', title),
            'analytic_account_id': project.analytic_account_id.id,
            'allocated_hours': allocated_hours,
            'partner_id': self.order_id.partner_id.id,
            'description': description,
            'project_id': project.id,
            'sale_line_id': self.id,
            'sale_order_id': self.order_id.id,
            'company_id': project.company_id.id,
            'user_ids': False,  # force non assigned task, as created as sudo()
        }