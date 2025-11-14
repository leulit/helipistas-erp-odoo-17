# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class LeulitAta(models.Model):
    _name = "leulit.ata"
    _description = "ATA Chapters"
    _rec_name = "display_name"

    ata_number = fields.Char(string="ATA Number")
    ata_name = fields.Char(string="ATA Chapter name")
    doble_check = fields.Boolean(string='Doble check')
    display_name = fields.Char(string="Display Name", compute='_compute_display_name', store=True)

    @api.depends('ata_number', 'ata_name')
    def _compute_display_name(self):
        for item in self:
            item.display_name = '[%s]-%s' % (item.ata_number, item.ata_name)