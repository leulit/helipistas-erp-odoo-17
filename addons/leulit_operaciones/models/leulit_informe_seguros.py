# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_seguro_report(models.Model):
    _name        = "leulit.seguro_report"
    _description = "leulit_seguro_report"
    _auto = False


    helicoptero = fields.Char('Helicóptero')
    vuelo = fields.Char('Vuelo')
    fecha = fields.Date('Fecha')
    hora_salida = fields.Float('Hora de salida')
    airtime = fields.Float('Airtime')
    fecha_anterior_vuelo = fields.Date('Fecha anterior vuelo')
    diferencia = fields.Integer('Días anterior')


    def init(self):
        tools.drop_view_if_exists(self._cr, 'leulit_seguro_report')
        self._cr.execute('''CREATE OR REPLACE VIEW leulit_seguro_report AS 
            (
                SELECT
                    row_number() OVER () AS id,
                    (select name from leulit_helicoptero where A.helicoptero_id = leulit_helicoptero.id) as helicoptero,
                    A.codigo as vuelo,
                    A.fechavuelo as fecha,
                    A.horasalida as hora_salida,
                    A.airtime as airtime,
                    CASE
                        WHEN A.helicoptero_id = B.helicoptero_id THEN B.fechavuelo
                        ELSE NULL
                    END	as fecha_anterior_vuelo,
                    CASE
                        WHEN A.helicoptero_id = B.helicoptero_id THEN (A.fechavuelo-B.fechavuelo)
                        ELSE NULL
                    END as diferencia
                FROM 
                (
                    SELECT RANK() OVER (ORDER BY helicoptero_id ASC, fechavuelo DESC, horasalida DESC) fila, id,  helicoptero_id, codigo, fechavuelo, horasalida, airtime, estado
                    FROM leulit_vuelo
                )A
                        
                LEFT OUTER JOIN
                (
                    SELECT RANK() OVER (ORDER BY helicoptero_id ASC, fechavuelo DESC, horasalida DESC) fila, id, helicoptero_id, codigo, fechavuelo, horasalida, airtime, estado
                    FROM leulit_vuelo
                )B ON A.FILA = B.FILA - 1
                WHERE
                    A.estado = 'cerrado'
                ORDER BY
                    A.helicoptero_id ASC,
                    A.fechavuelo DESC,
                    A.horasalida DESC
            )
            '''
        )



