
from odoo import api, exceptions, fields, models, _


class Survey(models.Model):
    _inherit = 'survey.survey'


    company_id = fields.Many2one(comodel_name="res.company", string="Compañía", required=True)