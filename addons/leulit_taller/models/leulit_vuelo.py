# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_vuelo(models.Model):
    _inherit = "leulit.vuelo"


    def get_motor(self, idvuelo):
        idmotor = False
        if isinstance(idvuelo, list):
            idvuelo = idvuelo[0]
        item = self.browse(idvuelo)
        if item:
            datosMotor = self.env['leulit.helicoptero_pieza'].get_datos_motor_instalado_in_fecha(item.helicoptero_id.id, item.fechavuelo)
            if datosMotor:
                idmotor = datosMotor.pieza
        return idmotor

    def acumulados_between_dates(self, helicoptero, fechainicio, fechafin):
        if not fechafin:
            fechafin = utilitylib.getStrToday()
        sql = """
            SELECT 
                COALESCE(SUM(vuelo.airtime),0) as suma_airtime,
                COALESCE(SUM(vuelo.ngvuelo),0) as suma_ng,
                COALESCE(SUM(vuelo.nfvuelo),0) as suma_nf,
                COALESCE(SUM(vuelo.tiemposervicio),0) as suma_tiemposervicio
            FROM 
                leulit_vuelo as vuelo
            WHERE 
                vuelo.estado = 'cerrado' 
                AND vuelo.fechasalida::DATE <= '{0} 23:59:59'::TIMESTAMP
                AND vuelo.fechavuelo::DATE >= '{1}'::DATE
                AND vuelo.helicoptero_id = {2}
        """.format(fechafin,fechainicio,helicoptero)
        self._cr.execute(sql)
        rows = self._cr.fetchall()
        return rows
