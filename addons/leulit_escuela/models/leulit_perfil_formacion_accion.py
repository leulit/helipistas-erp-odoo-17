# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_perfil_formacion_accion(models.Model):
    _name = "leulit.perfil_formacion_accion"
    _description = "leulit_perfil_formacion_accion"
    _rec_name = "descripcion"
    _order = "descripcion"



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


    @api.depends('remainder_dy','marge_dy')
    def _get_semaforo_dy(self):
        for item in self:
            if item.remainder_dy <= 0 :
                item.semaforo_dy = 'red'
            else:
                if item.remainder_dy < item.marge_dy:
                    item.semaforo_dy = 'yellow'
                else:
                    item.semaforo_dy = 'green'


    def done_course(self):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_perfil_formacion_done_accion_form')
        view_id = view_ref and view_ref[1] or False

        for item in self:
            context = {'default_pf_accion': item.id,
                        'default_done_date': datetime.now().strftime(DATE_FORMAT)}

        return {
            'type': 'ir.actions.act_window',
            'name': 'Marcar accción como realizado',
            'res_model': 'leulit.perfil_formacion_accion_last_done',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
        


    descripcion = fields.Char("Descriptor")
    notas = fields.Text('Notas')
    periodicidad_dy = fields.Integer('Periodicidad dy')
    marge_dy = fields.Integer('Margen dy')
    perfil_formacion = fields.Many2one('leulit.perfil_formacion', 'Perfil formación')
    inactivo = fields.Boolean(related='perfil_formacion.inactivo',string='Perfil inactivo')
    piloto = fields.Many2one(related='perfil_formacion.piloto',comodel_name='leulit.piloto',string='Piloto')
    alumno = fields.Many2one(related='perfil_formacion.alumno',comodel_name='leulit.alumno',string='Alumno')
    is_template = fields.Boolean('Es plantilla')
    pf_curso_tmpl = fields.Many2one('leulit.perfil_formacion_curso', 'Perfil formación curso')
    last_done_history = fields.One2many('leulit.perfil_formacion_accion_last_done', 'pf_accion','Historial last done')
    last_done = fields.One2many('leulit.perfil_formacion_accion_last_done', 'pf_accion', 'Last done',domain=[('is_last', '=', True)])
    last_done_date = fields.Date(related='last_done.done_date',string='Done date')
    next_done_date = fields.Date(compute=_get_next_done_date,string='N. done (DY)',store=False)
    remainder_dy = fields.Integer(compute=_get_remainder_dy,string='Remainder (DY)',store=False)
    semaforo_dy = fields.Char(compute=_get_semaforo_dy,string='Semáforo',store=False)
