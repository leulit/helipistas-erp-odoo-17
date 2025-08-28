# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_ruta(models.Model):
    _name           = "leulit.ruta"
    _description    = "leulit_ruta"
    _rec_name       = "nombre"

    @api.depends('aerovia_ids')
    def _setWaterZoneByAerovia(self):
        for item in self:
            item.water_zone = False
            for aerovia in item.aerovia_ids:
                if aerovia.aerovia_id.water_zone == True:
                    item.water_zone = True


    def _searchIsWaterZone(self, operator, value):
        ids = []
        for item in self.search([]):
            for aerovia in item.aerovia_ids:
                if aerovia.aerovia_id.water_zone == value:
                    ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]
    

    nombre = fields.Char('Nombre', size=500,required=True)
    comentarios = fields.Text('Comentarios')
    fecha_creacion = fields.Date('Fecha creación',required=True)
    fecha_aprobacion = fields.Date('Fecha aprobación',required=True)
    aerovia_ids = fields.One2many('leulit.rel_ruta_aerovia', 'ruta_id', 'Aerovías', required=True)
    activo = fields.Boolean('Activo')
    origen_id = fields.Many2one('leulit.helipuerto', 'Helipuerto Origen')
    destino_id = fields.Many2one('leulit.helipuerto', 'Helipuerto Destino')
    doc_origen_id = fields.Many2one('ir.attachment', 'Documento Origen')
    doc_destino_id = fields.Many2one('ir.attachment', 'Documento Destino')
    data_origen_id = fields.Binary(related='doc_origen_id.datas',string='',store=False)
    data_destino_id = fields.Binary(related='doc_destino_id.datas',string='',store=False)
    water_zone = fields.Boolean(compute=_setWaterZoneByAerovia,string="Zona autorotativa sobre el agua", search=_searchIsWaterZone)
