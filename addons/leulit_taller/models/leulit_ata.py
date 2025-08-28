# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class LeulitAta(models.Model):
    _name = "leulit.ata"
    # _rec_name = "complete_name"


    @api.depends('ata_number','ata_name')
    def name_get(self):
        res = []
        for item in self:
            res.append((item.id, '[%s]-%s' % (item.ata_number, item.ata_name)))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|',
            ('ata_number', operator, name),
            ('ata_name', operator, name)
        ]
        records = self.search(domain, limit=limit)
        return records.name_get()

    ata_number = fields.Char(string="ATA Number")
    ata_name = fields.Char(string="ATA Chapter name")
    doble_check = fields.Boolean(string='Doble check')

    