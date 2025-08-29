# -- encoding: utf-8 --

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime



class leulit_actividad_vuelo(models.Model):
    _name = "leulit.actividad_vuelo"
    _description = "leulit_actividad_vuelo"


    # def add_perfil_formacion(self, cr, uid, ids, context=None):
    #     view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hlp_perfil_formacion', 'helipistas_add_perfil_formacion_popup_form')
    #     view_id = view_ref and view_ref[1] or False        
    #     this = self.browse(cr, uid, ids, context=context)[0]        
    #     if context is None:
    #         context = {}
    #     context = {
    #         'master_id': this.id
    #     }
    #     return {
    #         'type'           : 'ir.actions.act_window',
    #         'name'           : 'Añadir Perfiles de Formación a la Actividad',
    #         'res_model'      : 'helipistas.add_perfil_formacion_popup',
    #         'view_type'      : 'form',
    #         'view_mode'      : 'form',
    #         'view_id'        : view_id,
    #         'target'         : 'new',
    #         'nodestroy'      : True,
    #         'context'        : context,
    #     }
        


    name = fields.Char('Actividad',required=True)
    pformacio_ids = fields.One2many('leulit.perfil_formacion', 'actividad_id', 'Perfil Formación')