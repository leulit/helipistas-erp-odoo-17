# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class leulit_rel_ruta_aerovia(models.Model):
    _name           = "leulit.rel_ruta_aerovia"
    _description    = "leulit_rel_ruta_aerovia"
    _order          = "sequence asc"
    _rec_name       = "aerovia_id"

    
    aerovia_id = fields.Many2one('leulit.ruta_aerovia', 'Aerovía', required=True, domain=[('activo','=',True)])
    ruta_id = fields.Many2one('leulit.ruta', 'Ruta', required=True)
    sequence = fields.Integer('sequence')
    distancia = fields.Float(related='aerovia_id.distancia',string='NM',store=False)
    rumbo = fields.Float(related='aerovia_id.rumbo',string='Rumbo (º)',store=False)
    altitudprevista = fields.Float(string='Altitud prevista (p)')
    altitudseguridad = fields.Float(related='aerovia_id.altitudseguridad',string='Altitud de seguridad (p)',store=False)
    start_point = fields.Many2one(related='aerovia_id.start_point_id',comodel_name="leulit.ruta_punto",string='Origen',store=False)
    end_point = fields.Many2one(related='aerovia_id.end_point_id',comodel_name="leulit.ruta_punto",string='Destino',store=False)
    idaerovia = fields.Integer(related='aerovia_id.id',string='ID Aerovía',store=False)
    water_zone = fields.Boolean(related='aerovia_id.water_zone',string="Zona autorotativa sobre el agua")



    @api.constrains("altitudprevista")
    def _check_altura_prevista(self):
        for item in self:
            if item.altitudprevista == 0:
                raise UserError("Se ha de indicar la altura prevista, y no puede ser 0.")
