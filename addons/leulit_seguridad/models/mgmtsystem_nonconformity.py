
from odoo import _, api, fields, models


class MgmtsystemNonconformity(models.Model):
    _inherit = "mgmtsystem.nonconformity"


    @api.depends("description")
    def _compute_short_description(self):
        for record in self:
            record.short_description = record.description[:100] if record.description else ""

    short_description = fields.Char(
        "Description",
        compute="_compute_short_description",
        store=True,
        readonly=True,
    )
