# -*- encoding: utf-8 -*-
from odoo import models, fields, api


class LeulitNdaAcuerdo(models.Model):
    _name = "leulit.nda.acuerdo"
    _description = "leulit_nda_acuerdo"
    _order = "id desc"

    version = fields.Char(string="Versión", required=True, default="1.0")
    contenido = fields.Html(string="Texto del acuerdo", required=True)
    active = fields.Boolean(string="Activo", default=True)

    @api.model
    def get_current(self):
        return self.search([("active", "=", True)], order="id desc", limit=1)
