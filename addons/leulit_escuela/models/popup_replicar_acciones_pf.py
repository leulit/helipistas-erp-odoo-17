# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)



class leulit_popup_replicar_acciones_pf(models.Model):
    _name           = "leulit.popup_replicar_acciones_pf"
    _description    = "leulit_popup_replicar_acciones_pf"
    
    def metodo_popup_a_ejecutar(self):
        for item in self:
            pf_tmpl = self.env['leulit.perfil_formacion'].browse(item.perfil_formacion_tmpl.id)
            for accion_tmpl in pf_tmpl.acciones:
                for accion in item.perfil_formacion_replica_ids:
                    pf = self.env['leulit.perfil_formacion'].browse(accion.id)
                    cont = 0
                    accion_vals = {
                        'descripcion': accion_tmpl.descripcion,
                        'notas': accion_tmpl.notas,
                        'periodicidad_dy': accion_tmpl.periodicidad_dy,
                        'marge_dy': accion_tmpl.marge_dy,
                        'perfil_formacion': accion.id,
                        'is_template': False,
                        'pf_curso_tmpl': accion_tmpl.id,       
                    }
                    for accion_pf in pf.acciones:
                        if accion_pf.pf_curso_tmpl.id == accion_tmpl.id:
                            accion_pf.write(accion_vals)
                            cont += 1  # Corregido: era =+ en lugar de +=
                    if cont == 0:
                        # Crear la acción directamente sin usar write()
                        self.env['leulit.perfil_formacion_accion'].create(accion_vals)
        return True

    perfil_formacion_tmpl = fields.Many2one(comodel_name='leulit.perfil_formacion', string='Perfil Formación')
    perfil_formacion_replica_ids = fields.Many2many(comodel_name='leulit.perfil_formacion', relation='leulit_relation_perfil_formacion_accion', column1='popup_rel', column2='perfil_formacion_accion_id',string='Perfil Formación', required=True)