# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)



class ReplicarPFAcciones(models.TransientModel):
    _name           = "leulit.popup_replicar_pf_acciones"
    _description    = "leulit_popup_replicar_pf_acciones"
    
    def metodo_popup_a_ejecutar(self):
        for item in self:
            for accion_tmpl in item.perfil_formacion_tmpl.acciones_new:
                for pf in item.perfil_formacion_replica_ids:
                    cont = 0
                    accion_vals = {
                        'accion': accion_tmpl.accion.id,
                        'periodicidad_dy': accion_tmpl.periodicidad_dy,
                        'margen_dy': accion_tmpl.margen_dy,
                        'perfil_formacion': pf.id
                    }
                    for accion_pf in pf.acciones_new:
                        if accion_pf.accion.id == accion_tmpl.accion.id:
                            accion_pf.write(accion_vals)
                            cont=+1
                    if cont == 0:
                        accion_tmpl.copy(default={'perfil_formacion': pf.id})
        return True
    


    def replicar_accion_to_perfiles(self):
        for item in self:
            for pf in item.perfil_formacion_replica_ids:
                flag = False
                for accion_pf in pf.acciones_new:
                    if accion_pf.accion.id == item.pf_accion.accion.id:
                        flag = True
                if not flag:
                    item.pf_accion.copy(default={'perfil_formacion': pf.id})

        return {'type': 'ir.actions.act_window_close'}

    perfil_formacion_tmpl = fields.Many2one(comodel_name='leulit.perfil_formacion', string='Perfil Formación')
    perfil_formacion_replica_ids = fields.Many2many(comodel_name='leulit.perfil_formacion', relation='leulit_relation_pf_accion', column1='popup_rel', column2='perfil_formacion_accion_id',string='Perfil Formación', required=True)
    pf_accion = fields.Many2one(comodel_name="leulit.pf_accion", string="Acción")