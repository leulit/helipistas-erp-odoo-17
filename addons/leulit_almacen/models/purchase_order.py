from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_locked = fields.Boolean(string='Pedido Enviado', default=False)

    def toggle_lock(self):
        for order in self:
            order.is_locked = not order.is_locked
