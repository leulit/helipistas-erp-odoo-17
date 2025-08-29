# -*- encoding: utf-8 -*-

from odoo import models, fields

class leulit_popup_perfil_formacion(models.TransientModel):
    _name = "leulit.popup_perfil_formacion"
    _description = "leulit_popup_perfil_formacion"

    def metodo_popup_a_ejecutar(self):
        nombre = ''
        for item in self:
            nombre = item.master_id.name + " - [ " + item.alumno.name + " ] "
            perfil_form_vals = {
                'name': nombre,
                'perfil_tmpl': item.master_id.id,
                'is_template': False,
                'alumno': item.alumno.id,
                'inactivo': False
            }
            perfil_form = self.env['leulit.perfil_formacion'].create(perfil_form_vals)
            cursos = []
            acciones = []
            acciones_new = []
            curso = False
            for item2 in item.master_id.cursos:
                if item2.curso:
                    curso = item2.curso.id
                curso_vals = {
                    'curso': curso,
                    'descripcion': item2.descripcion,
                    'notas': item2.notas,
                    'periodicidad_dy': item2.periodicidad_dy,
                    'marge_dy': item2.marge_dy,
                    'perfil_formacion': perfil_form,
                    'is_template': False,
                    'pf_curso_tmpl': item2.id,
                }
                cursos.append((0, 0, curso_vals))
            perfil_form.write({'cursos': cursos})
            for item2 in item.master_id.acciones_new:
                accion_new_vals = {
                    'accion': item2.accion.id,
                    'periodicidad_dy': item2.periodicidad_dy,
                    'margen_dy': item2.margen_dy,
                    'perfil_formacion': perfil_form,
                }
                acciones_new.append((0, 0, accion_new_vals))
            perfil_form.write({'acciones_new': acciones_new})

    piloto = fields.Many2one(comodel_name='leulit.piloto', string='Piloto')
    usuario = fields.Many2one(comodel_name='res.users', string='Usuario')
    alumno = fields.Many2one(comodel_name='leulit.alumno', string='Alumno')
    master_id = fields.Many2one(comodel_name='leulit.perfil_formacion', string='Pérfil de formación')
    is_piloto_externo = fields.Boolean(string='Piloto externo')


