# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_helicoptero_oilreport(models.Model):
    _name           = "leulit.helicoptero_oilreport"
    _description    = "leulit_helicoptero_oilreport"
    _auto           = False
    _rec_name       = 'id'


    helicoptero_id = fields.Many2one('leulit.helicoptero', 'Helicóptero', required=True, domain="[('baja','=',False)]")
    matricula = fields.Char('Matrícula', size=50, readonly=True)
    fecha = fields.Datetime('Fecha',readonly=True)
    oilqty = fields.Float('Aceite añadido (l.)', reaonly=True)
    acumulado = fields.Float('Cantidad acumulada (l.)', reaonly=True)
    airtimeacumulado = fields.Float('Airtime acumulado (hh:mm)', reaonly=True)
    baja_helicoptero = fields.Boolean(related='helicoptero_id.baja',string='Baja Helicóptero',store=False)



    # def init(self):
    #     tools.drop_view_if_exists(self._cr, 'leulit_helicoptero_oilreport')
    #     self._cr.execute("""
    #         CREATE OR REPLACE VIEW leulit_helicoptero_oilreport AS (
                
    #             SELECT
    #                 a.id,
    #                 a.helicoptero_id,
    #                 leulit_helicoptero."name" as matricula, 
    #                 a.fechasalida as fecha, 
    #                 a.oilqty,
    #                 (SELECT 
    #                     SUM(b.oilqty)
    #                 FROM 
    #                     leulit_vuelo b
    #                 WHERE 
    #                     b.fechasalida <= a.fechasalida and b.helicoptero_id = a.helicoptero_id) 
    #                 AS acumulado,
    #                 (SELECT 
    #                     SUM(b.airtime)
    #                 FROM 
    #                     leulit_vuelo b
    #                 WHERE 
    #                     b.fechasalida <= a.fechasalida and b.helicoptero_id = a.helicoptero_id) 
    #                 AS airtimeacumulado
    #             FROM 
    #                 leulit_vuelo as a 
    #                 INNER JOIN leulit_helicoptero ON a.helicoptero_id = leulit_helicoptero."id"
    #             WHERE 
    #                 a.oilqty > 0
    #             ORDER BY a.fechasalida DESC
    #         )""")
