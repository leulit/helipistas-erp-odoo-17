# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)

_actividades = []
_planificada = False

class leulit_leulit_actividad_base_rutas(models.Model):
    _name = "leulit.actividad_base_rutas"
    _description = "leulit_actividad_base_rutas"
    _auto = False



    def init(self):
        tools.drop_view_if_exists(self._cr, 'leulit_actividad_base_rutas')
        self._cr.execute(""" CREATE OR REPLACE VIEW leulit_leulit_actividad_base_rutas AS 
            (
                select * from
                (select
                    id,fecha,partner,
                    (select count(id) from leulit_actividad_base where UPPER(descripcion) LIKE '%RUTA CLH%' and fecha = t1.fecha and partner = t1.partner and prevista='f') as ruta_clh,
                    (select count(id) from leulit_actividad_base where UPPER(descripcion) LIKE '%RUTA ENAGAS%' and fecha = t1.fecha and partner = t1.partner and prevista='f') as ruta_enagas,
                    (select count(id) from leulit_actividad_base where UPPER(descripcion) LIKE '%RUTA GAS NATURAL%' and fecha = t1.fecha and partner = t1.partner and prevista='f') as ruta_gas_natural,
                    (select count(id) from leulit_actividad_base where UPPER(descripcion) LIKE '%RUTA AGUAS DE TARRAGONA%' and fecha = t1.fecha and partner = t1.partner and prevista='f') as ruta_aguas,
                    (select count(id) from leulit_actividad_base where UPPER(descripcion) LIKE '%GUARDIA%' and UPPER(descripcion) LIKE '%BOMBEROS%' and fecha = t1.fecha and partner = t1.partner and prevista='f') as guardia_bomberos
                FROM
                    leulit_actividad_base as t1
                ) as t2 
            )
        """)    
    
    

    fecha = fields.Date("Fecha", index=True)
    partner = fields.Many2one('res.partner', 'Usuario', index=True)
    ruta_clh = fields.Integer("RUTA CLH")
    ruta_enagas = fields.Integer("RUTA ENGAS")
    ruta_gas_natural = fields.Integer("RUTA GAS NATURAL")
    ruta_aguas = fields.Integer("RUTA AGUAS DE TARRAGONA")
    guardia_bomberos = fields.Integer("GUARDIA BOMBEROS")
