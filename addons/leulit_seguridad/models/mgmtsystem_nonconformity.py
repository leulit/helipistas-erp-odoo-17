
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
    partner_id = fields.Many2one("res.partner", "Partner", required=False)
    create_date = fields.Datetime("Creado en", readonly=False)

    def write(self, vals):
        create_date = vals.pop("create_date", None)
        res = super().write(vals)
        if create_date:
            self._cr.execute(
                "UPDATE mgmtsystem_nonconformity SET create_date = %s WHERE id IN %s",
                (create_date, tuple(self.ids)),
            )
            self.invalidate_recordset(["create_date"])
        return res