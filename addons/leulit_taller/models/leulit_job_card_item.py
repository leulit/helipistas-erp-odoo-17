# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
import logging

_logger = logging.getLogger(__name__)


class LeulitJobCardItem(models.Model):
    _name = "leulit.job_card_item"
    _rec_name = "descripcion"


    descripcion = fields.Char(string="Descripción")
    solucion = fields.Char(string="Solución Defecto")
    equipamiento_id = fields.Many2one(comodel_name="maintenance.equipment", string="Equipo")
    manual_id = fields.Many2one(comodel_name="leulit.maintenance_manual", string="Manual")
    job_card_id = fields.Many2one(comodel_name="leulit.job_card", string="Job Card")
    doble_check = fields.Boolean(string='Doble check')
    boroscopia = fields.Boolean(string='Boroscopia')
    inspeccion_seguridad = fields.Boolean(string='Inspección seguridad')
    oblig_form_one = fields.Boolean(string='Obligatoriedad Form One')
    no_aplica = fields.Boolean(string='N/A')
    tiempo_defecto = fields.Float(string="Tiempo por defecto")
    type_maintenance = fields.Selection(selection=[('A', 'A'), ('B', 'B'), ('C','C')], string="Tipo")
    ata_ids = fields.Many2many(comodel_name="leulit.ata", relation="leulit_jcitem_ata" , column1="job_card_item_id" , column2="ata_id", string="ATAs")
    certificacion_ids = fields.Many2many(comodel_name="leulit.certificacion", relation="leulit_jcitem_certificacion" , column1="job_card_item_id" , column2="certificacion_id", string="Certificaciones")
