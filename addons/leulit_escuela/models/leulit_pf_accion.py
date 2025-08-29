# -*- encoding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class PFAccion(models.Model):
    _name = "leulit.pf_accion"
    _description = "leulit.pf_accion"
    rec_name = "accion"


    @api.depends('last_done_date','periodicidad_dy')
    def _get_next_done_date(self):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        for item in self:
            if item.periodicidad_dy == 0:
                item.next_done_date = None
            else:
                if item.last_done_date:
                    end_date = item.last_done_date + timedelta(days=item.periodicidad_dy)
                    item.next_done_date = end_date.strftime(DATE_FORMAT)
                else:
                    item.next_done_date = None
    
    @api.depends('next_done_date')
    def _get_remainder_dy(self):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        for item in self:
            if item.next_done_date:
                hoy = datetime.now().date()
                diasrestantes = (item.next_done_date - hoy).days                
                item.remainder_dy = diasrestantes
            else:
                item.remainder_dy = 0

    @api.depends('remainder_dy','margen_dy')
    def _get_semaforo_dy(self):
        for item in self:
            if item.remainder_dy <= 0 :
                item.semaforo_dy = 'red'
            else:
                if item.remainder_dy < item.margen_dy:
                    item.semaforo_dy = 'yellow'
                else:
                    item.semaforo_dy = 'green'

    @api.onchange("accion")    
    def onchange_accion(self):
        if self.accion:
            self.periodicidad_dy = self.accion.periodicidad_dy
            self.margen_dy = self.accion.margen_dy
    
    def delete_accion(self):
        self.unlink()
    
    def replicar_accion_to_perfiles(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20230307_1114_form')
        view_id = view_ref and view_ref[1] or False 
        context = {
            'default_pf_accion': self.id,
            'default_perfil_formacion_tmpl': self.perfil_formacion.id,
        }
        return {
                'type'           : 'ir.actions.act_window',
                'name'           : 'Replicar Acción Perfil Formación',
                'res_model'      : 'leulit.popup_replicar_pf_acciones',
                'view_mode'      : 'form',
                'view_id'        : view_id,
                'target'         : 'new',
                'nodestroy'      : True,
                'context'        : context,
        }

    accion = fields.Many2one(comodel_name="leulit.accion", string="Acción")
    periodicidad_dy = fields.Integer('Periodicidad dy')
    margen_dy = fields.Integer('Margen dy')
    perfil_formacion = fields.Many2one('leulit.perfil_formacion', 'Perfil formación')
    is_template = fields.Boolean(related='perfil_formacion.is_template',string='¿Es plantilla?')
    inactivo = fields.Boolean(related='perfil_formacion.inactivo',string='Perfil inactivo')
    alumno = fields.Many2one(related='perfil_formacion.alumno',comodel_name='leulit.alumno',string='Alumno')
    realizados_last_done = fields.One2many('leulit.pf_accion_last_done', 'pf_accion', 'Realizados')
    last_done = fields.One2many('leulit.pf_accion_last_done', 'pf_accion', 'Last done',domain=[('is_last', '=', True)])
    last_done_date = fields.Date(related='last_done.done_date',string='Done date')
    next_done_date = fields.Date(compute=_get_next_done_date,string='N. done (DY)',store=False)
    remainder_dy = fields.Integer(compute=_get_remainder_dy,string='Remainder (DY)',store=False)
    semaforo_dy = fields.Char(compute=_get_semaforo_dy,string='Semáforo',store=False)

    def done_course(self):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20230125_1144_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_pf_accion': self.id,
            'default_name': self.accion.name,
            'default_done_date': datetime.now().strftime(DATE_FORMAT)
        }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Marcar accción como realizado',
            'res_model': 'leulit.pf_accion_last_done',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }