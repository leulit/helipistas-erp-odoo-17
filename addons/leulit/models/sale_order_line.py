from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        if self.env.context.get('skip_delivery', False):
            return True
        return super(SaleOrderLine, self)._action_launch_stock_rule(previous_product_uom_qty)