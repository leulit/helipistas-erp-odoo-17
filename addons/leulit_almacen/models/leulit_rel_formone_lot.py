# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class LeulitRelFormOneLot(models.Model):
    _inherit = "leulit.rel_formone_lot"


    descripcion_pieza = fields.Char(related="pieza_id.product_id.name",string="Description")
    pn = fields.Char(related="pieza_id.product_id.default_code",string="Part Number")
    sn = fields.Char(related="pieza_id.sn",string="Serial Number")