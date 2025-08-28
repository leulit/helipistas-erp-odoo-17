# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_helicoptero_pieza(models.Model):
    _name = "leulit.helicoptero_pieza"
    _description = "leulit_helicoptero_pieza"
    _order = "from_date desc"
    _rec_name = "helicoptero"



    def get_datos_motor_instalado_in_fecha(self, helicoptero_id, fecha):
        result = False
        sql = """
                    SELECT id
                    FROM
                        leulit_helicoptero_pieza
                    WHERE
                        helicoptero = {1}
                    AND
                        from_date <= '{0}'::DATE
                    AND
                        (
                            to_date >= '{0}'::DATE
                            OR
                            to_date IS NULL
                        )
                    AND 
                        is_motor = 't'
                """.format(fecha, helicoptero_id)
        #_logger.error("-->get_datos_motor_instalado_in_fecha--> sql = %r", sql)
        rows = utilitylib.runQuery(self._cr, sql)
        if len(rows) > 0:
            ids = [x['id'] for x in rows]
            return self.browse(ids)
        return result


    def get_idpieza_motor_activo(self, helicoptero_id):
        result = False
        try:
            ids = self.search([('helicoptero', '=', helicoptero_id),('is_motor','=',True),('instalado_actualmente','=',True)])
            if ids:
                for item in ids:
                    result = item.pieza
        except Exception as exc:
            result = False
        return result

    def _instalado_actualmente(self):
        for item in self:
            if not item.to_date:
                item.instalado_actualmente = True
            else:
                if item.to_date < utilitylib.objFechaToStr(datetime.now()):
                    item.instalado_actualmente = False
                else:
                    item.instalado_actualmente = True



    helicoptero = fields.Many2one('leulit.helicoptero', 'Helicóptero')
    modelo = fields.Selection(related='helicoptero.modelo.tipo',string='Modelo',store=False) #utilitylib.hlp_get_tipos_helicopteros()
    producto = fields.Many2one('product.product', 'Pieza')
    is_motor = fields.Boolean("Motor")
    is_life_limit = fields.Boolean("Life limit")
    is_rotable = fields.Boolean('Rotable')
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')
    #FECHA DEL ÚLTIMO OVERHAUL AL INSTALAR LA PIEZA.
    fecha_overhaul = fields.Date('Fecha overhaul')
    # fecha_fab = fields.Date(related='producto.anofabmoto',string='Fecha fabricación',store=False)
    # Valor de TSN actual
    #TODO-function tsn = fields.Float(compute='_get_tsn',string='TSN',store=False)

    # HORAS DE VUELO QUE TENÍA LA PIEZA AL INSTALARLA. AL INICIAR EL PERIODO
    horas_inicio = fields.Float('Horas inicio')

    # ACUMULADO DE HORAS DURANTE EL PERIODO DE INSTALACIÓN
    #TODO-function airtime = fields.Float(compute='_airtime',string='Airtime',store={'leulit.vuelo': (_store_ids_piezas, [], 10),},fnct_inv=_common_fnct_inv_float)
    # HORAS DE VUELO DESDE EL ÚLTIMO OVERHAUL QUE TENÍA LA PIEZA AL INSTALARLA.
    tso_inicio = fields.Float("Horas desde overhaul")
    # ACUMULADO DE HORAS DURANTE EL PERIODO DE INSTALACIÓN
    #TODO-function tso = fields.Float(compute='_get_tso',string='TSO')
    #TODO-function tsi = fields.Float(compute='_get_tsi',string='TSI')
    instalado_actualmente = fields.Boolean(compute='_instalado_actualmente',string='Instalado actualmente',store=True)
    #TODO-function ng = fields.Float(compute='_get_ng',string='NG')
    # ACUMULADO DE NG DURANTE EL PERIODO DE INSTALACIÓN
    #TODO-function ng_acumulado = fields.Float(compute='_ng_acumulado',string='NG acumulado',store={'leulit.vuelo': (_store_ids_piezas, [], 10),},fnct_inv=_common_fnct_inv_float)
    # NG QUE TENÍA LA PIEZA AL INSTALARLA. AL INICIAR EL PERIODO
    ng_start = fields.Float('NG inicio')

    tacometro_start = fields.Float('Tacómetro inicio')
    tacometro = fields.Float('Tacómetro acumulado')

    #TODO-function nf = fields.Float(compute='_get_nf',string='NF')
    # NF QUE TENÍA LA PIEZA AL INSTALARLA. AL INICIAR EL PERIODO
    nf_start = fields.Float('NF inicio')
    # ACUMULADO DE NF DURANTE EL PERIODO DE INSTALACIÓN
    #TODO-function nf_acumulado = fields.Float(compute='_nf_acumulado',string='NF acumulado',store={'leulit.vuelo': (_store_ids_piezas, [], 10),},fnct_inv=_common_fnct_inv_float)
    # o_life_hours = fields.Float(related='producto.o_life_hours',string='Horas vida operativa',store=False)
    # o_life_days = fields.Integer(related='producto.o_life_days',string='Días operativa',store=False)
    #TODO-function hours_remaining = fields.Float(compute='_hours_remaining',string='Hours R.')
    #TODO-function days_remaining = fields.Integer(compute='_days_remaining',string='Days R.')