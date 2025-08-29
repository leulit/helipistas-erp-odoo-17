# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class leulit_popup_replicar_cursos_pf(models.TransientModel):
    _name           = "leulit.popup_replicar_cursos_pf"
    _description    = "leulit_popup_replicar_cursos_pf"

    def metodo_popup_a_ejecutar(self):
        for item in self:
            # bucle de cursos del template
            for curso_tmpl in item.perfil_formacion_tmpl.cursos:
                # bucle de los perfiles de formacion seleccionados en el popup
                for pf in item.perfil_formacion_replica_ids:
                    cont = 0
                    curso_escuela = False
                    if curso_tmpl.curso:
                        curso_escuela = curso_tmpl.curso.id
                    # valores para el perfil_formacion_curso
                    curso_vals = {
                        'curso': curso_escuela,
                        'descripcion': curso_tmpl.descripcion,
                        'notas': curso_tmpl.notas,
                        'periodicidad_dy': curso_tmpl.periodicidad_dy,
                        'marge_dy': curso_tmpl.marge_dy,
                        'perfil_formacion': pf.id,
                        'is_template': False,
                        'pf_curso_tmpl': curso_tmpl.id,
                    }
                    # bucle de los cursos del perfil de formacion
                    for curso_pf in pf.cursos:
                        # Si coinicide el curso que ya esta en el perfil de formacion con el curso del template solo actualiza los datos
                        # si no entra en el if el contador no suma.
                        if curso_pf.pf_curso_tmpl.id == curso_tmpl.id:
                            curso_pf.write(curso_vals)
                            cont =+1
                    # si no hay ningun curso que coincida entre el perfil de formacion y el template, lo crea a pelo
                    if cont == 0:
                        pf.write({'cursos' : [(0 ,0, curso_vals)]})
                        # Busca si hay cursos realizados del alumno y lo realizamos con el ultimo regitro.
                        pf_curso_creado = self.env['leulit.perfil_formacion_curso'].search([('pf_curso_tmpl','=',curso_tmpl.id),('perfil_formacion','=',pf.id)])
                        another_pf_cursos = self.env['leulit.perfil_formacion_curso'].search([('curso','=',curso_escuela),('perfil_formacion','!=',pf.id),('alumno','=',pf.alumno.id)])
                        for a_pf_curso in another_pf_cursos:
                            last_done = self.env['leulit.perfil_formacion_curso_last_done'].search([('pf_curso','=',a_pf_curso.id),('is_last','=',True)])
                            if last_done:
                                last_done.copy(default={'pf_curso':pf_curso_creado.id})

        return {'type': 'ir.actions.act_window_close'}
    

    def end_course_template(self):
        for item in self:
            for pf in item.perfil_formacion_replica_ids:
                for curso_pf in pf.cursos:
                    if curso_pf.pf_curso_tmpl.id == item.pf_curso.id:
                        curso_pf.end_course()
            item.pf_curso.end_course()
        return {'type': 'ir.actions.act_window_close'}
    

    def start_course_template(self):
        for item in self:
            for pf in item.perfil_formacion_replica_ids:
                for curso_pf in pf.cursos_finalizados:
                    if curso_pf.pf_curso_tmpl.id == item.pf_curso.id:
                        curso_pf.start_course()
            item.pf_curso.start_course()
        return {'type': 'ir.actions.act_window_close'}


    def replicar_curso_to_perfiles(self):
        for item in self:
            for pf in item.perfil_formacion_replica_ids:
                flag = False
                for curso_pf in pf.cursos:
                    if curso_pf.pf_curso_tmpl.id == item.pf_curso.id:
                        flag = True
                for curso_pf in pf.cursos_finalizados:
                    if curso_pf.pf_curso_tmpl.id == item.pf_curso.id:
                        flag = True
                if not flag:
                    item.pf_curso.copy(default={'perfil_formacion': pf.id, 'is_template':False, 'pf_curso_tmpl': item.pf_curso.id})

        return {'type': 'ir.actions.act_window_close'}
    

    @api.depends('perfil_formacion_replica_ids')
    def _get_cursos_tmpl(self):
        for item in self:
            cursos = []
            if len(item.perfil_formacion_replica_ids) < 2:
                for curso_tmpl in item.perfil_formacion_tmpl.cursos:
                    flag=False
                    for pf in item.perfil_formacion_replica_ids:
                        for curso_pf in pf.cursos:
                            if curso_pf.pf_curso_tmpl.id == curso_tmpl.id:
                                flag=True
                        if not flag:
                            cursos.append(curso_tmpl.id)
            if len(cursos) == 0:
                cursos = False
            item.cursos_añadir = cursos


    perfil_formacion_tmpl = fields.Many2one(comodel_name='leulit.perfil_formacion', string='Perfil Formación')
    perfil_formacion_replica_ids = fields.Many2many(comodel_name='leulit.perfil_formacion', relation='leulit_relation_perfil_formacion', column1='popup_rel', column2='perfil_formacion_id',
                                                         string='Perfil Formación', required=True)
    pf_curso = fields.Many2one(comodel_name="leulit.perfil_formacion_curso", string="Curso")

    cursos_añadir = fields.One2many(compute=_get_cursos_tmpl ,comodel_name="leulit.perfil_formacion_curso", string="Cursos")
    
