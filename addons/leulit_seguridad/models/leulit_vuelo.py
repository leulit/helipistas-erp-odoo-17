# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_vuelo(models.Model):
    _name = "leulit.vuelo"
    _inherit = "leulit.vuelo"


    def isHelicopterBlocked(self, helicoptero_id, fechavuelo):
        return self.env["leulit.anomalia"].haveNoGo(helicoptero_id, fechavuelo)
    

    @api.depends('helicoptero_id','fechavuelo')
    def _get_anomalias(self):
        for item in self:
            if item.helicoptero_id:
                item.diferido_ids = self.env['leulit.anomalia'].get_anomalias_unsigned_by_helicoptero(item.helicoptero_id.id)
       
                
    # @api.depends('fechavuelo')
    # def _get_anomalias_by_fecha(self):
    #     for item in self:
    #          item.print_anomalia_ids = self.env['leulit.anomalia'].get_diferidos_by_fecha(item['fechavuelo'])


    @api.onchange('helicoptero_id', 'estado' , 'fechavuelo')
    def onchange_helicoptero_estado_fechavuelo(self):
        for item in self:
            item.diferido_ids = self.env['leulit.anomalia'].get_anomalias_unsigned_by_helicoptero(item.helicoptero_id.id)
        

    def wizard_add_anomalia(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_seguridad', 'leulit_20201026_0823_form')
        view_id = view_ref and view_ref[1] or False
        for item in self:
            context = {
                'curso_id'          : item.curso_id.id,
            }
        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Anomalía/Discrepancia',
           'res_model'      : 'leulit.anomalia',
           'view_type'      : 'form',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'context'        : context,
        }


    diferido_ids = fields.One2many(compute=_get_anomalias, string='Anomalías/Defeectos', store=False, comodel_name='leulit.anomalia')
    anomalia_ids = fields.One2many('leulit.anomalia', 'vuelo_id', string='Anomalías/Defectos', domain=[('estado', 'in', ['deferred', 'pending', 'flightcanceled'])])
    # print_anomalia_ids = fields.One2many(compute='_get_anomalias_by_fecha',string='Anomalías/Defectos',store=False,comodel_name='leulit.anomalia')
