# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class leulit_hist_16bravo(models.Model):
    _name = "leulit.hist_16bravo"
    _description = "leulit_hist_16bravo"

    def validarEntrada(self, vals):
        return True

    def create(self, vals):
        res = False
        if self.validarEntrada(vals):
            res = super(leulit_hist_16bravo, self).create(vals)
        return res
    
    def write(self, vals):
        res = False
        if self.validarEntrada(vals):
            res = super(leulit_hist_16bravo,self).write(vals)
        return res

    def actual(self, piloto_id):
        result = False
        itemIds = self.search([('piloto_id', '=', piloto_id)], order="fecha_ini desc", limit=1)
        if itemIds:
            if isinstance(itemIds, list):
                itemIds = itemIds[0]
            result = itemIds
        return result


    fecha_ini = fields.Date('Fecha inicio',required=True)
    fecha_fin = fields.Date('Fecha fin')
    piloto_id = fields.Many2one('leulit.piloto', 'Piloto')

    start_hv = fields.Float('Horas totales inicio')
    start_hv_pm = fields.Float('Horas piloto al mando inicio')
    start_hv_inst = fields.Float('Horas instructor inicio')
    start_hv_dm = fields.Float('Horas doble mando inicio')
    start_hv_date = fields.Date('Fecha inicio')
    
    start_hv_me = fields.Float('Horas ME inicio')
    start_hv_se = fields.Float('Horas SE inicio')
    start_hv_night = fields.Float('Horas nocturnas inicio')
    start_hv_ifr = fields.Float('Horas IFR inicio')

    time_flight_range1 = fields.Float(string="TV 28d",digits= dp.get_precision('leulit_2d_actividad_dp'))
    time_flight_range2 = fields.Float(string="TV 12 m.",digits= dp.get_precision('leulit_2d_actividad_dp'))
    time_flight_range3 = fields.Float(string="TV 3 m.",digits= dp.get_precision('leulit_2d_actividad_dp'))
    dias_tabajados_mes = fields.Integer('Dias Tr. mes')
