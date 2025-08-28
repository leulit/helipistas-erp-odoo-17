# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_ruta_aerovia(models.Model):
    _name           = "leulit.ruta_aerovia"
    _description    = "leulit_ruta_aerovia"
    _inherit        = ['mail.thread']
    _rec_name       = "name"

    '''
    def init(self, cr):
        ids = self.search(cr, SUPERUSER_ID, [])
        for item in self.browse(cr, SUPERUSER_ID, ids, {}):
            self.write(cr, SUPERUSER_ID, item.id, {'activo': item.activo})
    '''
    @api.depends('start_point_id','end_point_id')
    def _get_name(self):
        for item in self:
            tira = "..."
            if item.start_point_id and item.end_point_id:
                s1 = ""
                if item.start_point_id.indicativo:
                    s1 = "("+item.start_point_id.indicativo+") "
                if item.start_point_id.descripcion:
                    s1 = s1 + item.start_point_id.descripcion
                if s1 == "":
                    s1 = "..."
                s2 = ""
                if item.end_point_id.indicativo:
                    s2 = "("+item.end_point_id.indicativo+") "
                if item.end_point_id.descripcion:
                    s2 = s2 + item.end_point_id.descripcion
                if s2 == "":
                    s2 = "..."
                tira = s1+" - "+s2
            item.name = tira


    def _search_name(self, operator, value):
        ids = []
        for item in self.search([]):
            if item.start_point_id.indicativo:
                if value.lower() in item.start_point_id.indicativo.lower():
                    ids.append(item.id)
            if item.start_point_id.descripcion:
                if value.lower() in item.start_point_id.descripcion.lower():
                    ids.append(item.id)
            if item.end_point_id.indicativo:
                if value.lower() in item.end_point_id.indicativo.lower():
                    ids.append(item.id)
            if item.end_point_id.descripcion:
                if value.lower() in item.end_point_id.descripcion.lower():
                    ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]


    @api.depends('start_point_id','end_point_id')
    def _calc_distance(self):
        distance = 0
        for item in self:
            distance = utilitylib.calc_dist_fixed( item.start_point_id.latitud, item.start_point_id.longitud, item.end_point_id.latitud, item.end_point_id.longitud )
            distance = utilitylib.convert_metros_nauticmiles( distance )
            item.distancia = distance


    @api.depends('start_point_id','end_point_id')
    def _calc_rumbo(self):
        rumbo = 0
        for item in self:
            rumbo = utilitylib.calc_rumbo( item.start_point_id.latitud, item.start_point_id.longitud, item.end_point_id.latitud, item.end_point_id.longitud  )
            item.rumbo = rumbo


    def _get_aeroviasids(self):
        return self.search(['|',('start_point_id', 'in', self.ids ),('end_point_id', 'in', self.ids )])
    
    
    def _get_doc(self):
        for item in self:
            docs_ids = self.env['ir.attachment'].search([('res_model','=','leulit.ruta_aerovia'),('res_id','=',item.id)])
            if docs_ids:
                item.doc_id = docs_ids[0]
            else:
                item.doc_id = 0


    def _search_doc_id(self, operator, value):
        ids = False
        for item in self:
            ids = item.search([('doc_id','=',value)])
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]


    def xmlrpc_other_aerovias(self, iditem):
        puntos = []
        for item in self.search([('id','!=',iditem),('activo','=',True)]):
            puntos.append({
                'id' : item.id,
                'sp_lat' : item.sp_lat,
                'sp_lng' : item.sp_lng,
                'ep_lat' : item.ep_lat,
                'ep_lng' : item.ep_lng,
                'name' : item.name
            })
        return puntos
    

    def open_other_aerovia(self,id):
        _logger.error(id)
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones', 'leulit_20201026_1153_form')
        view_id = view_ref and view_ref[1] or False
        item_id = self.search([('id','=',id)]).id
        return {
            'view_id' : view_id,
            'item_id' : item_id
        }
    

    name = fields.Char(compute='_get_name', string='Descripción', search='_search_name', store=False)
    distancia = fields.Float(compute='_calc_distance', string='NM')
    rumbo = fields.Float(compute='_calc_rumbo',string='Rumbo (º)')
    altitudprevista = fields.Float('Altitud prevista (p)', required=False)
    altitudseguridad = fields.Float('Altitud de seguridad (p)',required=True)
    start_point_id = fields.Many2one('leulit.ruta_punto', 'Origen')
    sp_lat = fields.Float(related='start_point_id.latitud', string='', store=False)
    sp_lng = fields.Float(related='start_point_id.longitud', string='',store=False)
    end_point_id = fields.Many2one('leulit.ruta_punto', 'Destino')
    ep_lat = fields.Float(related='end_point_id.latitud', string='', store=False)
    ep_lng = fields.Float(related='end_point_id.longitud', string='', store=False)
    activo = fields.Boolean('Activo')
    doc_id = fields.Many2one(compute='_get_doc', comodel_name="ir.attachment", string='Documento', store=False, search=_search_doc_id)
    water_zone = fields.Boolean(string="Zona autorotativa sobre el agua",default=False)

    