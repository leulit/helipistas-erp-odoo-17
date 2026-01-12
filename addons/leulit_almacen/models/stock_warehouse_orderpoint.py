# -*- coding: utf-8 -*-

import logging

from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"


    @api.depends('product_id','product_id.optional_product_ids')
    def _get_pn_equivalencia(self):
        for item in self:
            pn_equiv = ""
            qty = 0
            if item.product_id:
                for x in item.product_id.optional_product_ids:
                    pn_equiv += x.default_code + "; "
                    qty += x.qty_available
            item.str_product_opcionales = pn_equiv
            item.qty_opcionales = qty

    
    str_product_opcionales = fields.Char(compute="_get_pn_equivalencia", string="PN alternativos")
    qty_opcionales = fields.Float(compute="_get_pn_equivalencia", string="Qty total alternativos")