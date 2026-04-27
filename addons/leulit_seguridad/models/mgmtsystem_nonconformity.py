
from odoo import _, api, fields, models, registry
import logging
import threading

_logger = logging.getLogger(__name__)


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
    responsible_user_id = fields.Many2one(
        "res.users", "Responsible", required=False, tracking=True
    )
    manager_user_id = fields.Many2one(
        "res.users", "Manager", required=False, tracking=True
    )
    origin_ids = fields.Many2many(
        "mgmtsystem.nonconformity.origin",
        "mgmtsystem_nonconformity_origin_rel",
        "nonconformity_id",
        "origin_id",
        "Origin",
        required=False,
    )

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

    def set_default_origin_on_nonconformity(self):
        _logger.error("################### set_default_origin_on_nonconformity")
        threaded_calculation = threading.Thread(target=self.run_set_default_origin_on_nonconformity)
        _logger.error("################### set_default_origin_on_nonconformity start thread")
        threaded_calculation.start()

    def run_set_default_origin_on_nonconformity(self):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            origin = env['mgmtsystem.nonconformity.origin'].sudo().browse(24)
            nonconformities = env['mgmtsystem.nonconformity'].sudo().search([
                ('origin_ids', '=', False)
            ])
            for nc in nonconformities:
                nc.write({'origin_ids': [(4, origin.id)]})
                new_cr.commit()
        _logger.error('################### set_default_origin_on_nonconformity fin thread')