# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class LeulitCertificacionAeronave(models.Model):
    _name = "leulit.certificacion_aeronave"
    _rec_name = "name"

    @api.depends('certificacion_id', 'aeronave')
    def _get_name(self):
        for item in self:
            aeronave_str = dict(self._fields["aeronave"].selection).get(item.aeronave)
            if item.certificacion_id:
                item.name = item.certificacion_id.name + ' - ' + aeronave_str


    name = fields.Char(compute=_get_name,string="Nombre")
    certificacion_id = fields.Many2one(comodel_name='leulit.certificacion', string='Certificación', required=True)
    aeronave = fields.Selection(selection=[('cabri_g2','Cabri G2'),('r22_r44','R22 / R44'),('ec_120','EC120')], string='Aeronave', required=True)
    color = fields.Integer()