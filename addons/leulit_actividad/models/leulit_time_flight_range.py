# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
import pytz
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp
import threading
from datetime import datetime, date, timedelta

from . import actividad_aerea
from . import actividad_laboral

import logging
_logger = logging.getLogger(__name__)


class LeulitTimeFlightRange(models.Model):
    _name = 'leulit.time_flight_range'
    _description = 'LeulitTimeFlightRange'
    _auto = False

    time_flight_range1 = fields.Float("Horas de vuelo 28 días")
    time_flight_range2 = fields.Float("Horas de vuelo 12 meses")
    time_flight_range3 = fields.Float("Horas de vuelo 3 meses")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW leulit_time_flight_range AS 
            (
                SELECT
                    T1.actividad_aerea as actividad_aerea,
                    T1.fecha,
                    T1.partner,
                    (
                        SELECT 
                            round( coalesce( SUM(leulit_item_actividad_aerea.tiempo),0),2)
                        FROM 
                            leulit_item_actividad_aerea 
                        WHERE 
                            leulit_item_actividad_aerea.fecha >= (T1.fecha - (INTERVAL '28 DAY'))
                        AND
                            leulit_item_actividad_aerea.fecha <= T1.fecha
                        AND
                            leulit_item_actividad_aerea.partner = T1.partner 
                        AND
                            leulit_item_actividad_aerea.modelo = 'leulit.vuelo'
                        AND
                            leulit_item_actividad_aerea.prevista = 'f'
                    ) as time_flight_range1,   
                    (
                        SELECT 
                            round( coalesce( SUM(leulit_item_actividad_aerea.tiempo),0),2)
                        FROM 
                            leulit_item_actividad_aerea 
                        WHERE 
                            leulit_item_actividad_aerea.fecha >= (T1.fecha - (INTERVAL '12 MONTH'))
                        AND
                            leulit_item_actividad_aerea.fecha <= T1.fecha
                        AND
                            leulit_item_actividad_aerea.partner = T1.partner 
                        AND
                            leulit_item_actividad_aerea.modelo = 'leulit.vuelo'
                        AND
                            leulit_item_actividad_aerea.prevista = 'f'
                    ) as time_flight_range2,   
                    (
                        SELECT 
                            round( coalesce( SUM(leulit_item_actividad_aerea.tiempo),0),2)
                        FROM 
                            leulit_item_actividad_aerea 
                        WHERE 
                            leulit_item_actividad_aerea.fecha >= (T1.fecha - (INTERVAL '84 DAY'))
                        AND
                            leulit_item_actividad_aerea.fecha <= T1.fecha
                        AND
                            leulit_item_actividad_aerea.partner = T1.partner 
                        AND
                            leulit_item_actividad_aerea.modelo = 'leulit.vuelo'
                        AND
                            leulit_item_actividad_aerea.prevista = 'f'
                    ) as time_flight_range3
                FROM
                    leulit_item_actividad_aerea as T1
            )
            '''
        )