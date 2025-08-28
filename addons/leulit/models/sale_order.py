# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class sale_order(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"
    _rec_name = "full_name"

    @api.depends('name', 'partner_id')
    def _get_full_name(self):
        for item in self:
            if item.name and item.partner_id:
                item.full_name = '[{0}] - {1}'.format(item.name,item.partner_id.name)


    @api.depends('partner_id', 'company_id')
    def _compute_partner_bank_id(self):
        for pay in self:
            available_partner_bank_accounts = pay.company_id.partner_id.bank_ids.filtered(lambda x: x.company_id in (False, pay.company_id))
            if available_partner_bank_accounts:
                if pay.partner_bank_id not in available_partner_bank_accounts:
                    pay.partner_bank_id = available_partner_bank_accounts[0]._origin
            else:
                pay.partner_bank_id = False
    
    def action_confirm_without_delivery(self):
        self = self.with_context(skip_delivery=True)
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))
        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write(self._prepare_confirmation_values())
        
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        return True


    full_name = fields.Char(compute=_get_full_name,string='Titulo',store=True)
    task_done = fields.Boolean(string='Tarea realizada')
    partner_bank_id = fields.Many2one('res.partner.bank', string="Banco destinatario",
        readonly=False, store=True,
        compute=_compute_partner_bank_id,
        domain="[('partner_id', '=', partner_id)]",
        check_company=True)
    