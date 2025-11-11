# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


    
class leulit_popup_rel_parte_escuela_cursos_alumnos(models.TransientModel):
    _name           = "leulit.popup_rel_parte_escuela_cursos_alumnos"
    _description    = "leulit_popup_rel_parte_escuela_cursos_alumnos"


    def xmlrpc_asignaturas(self, idcurso, alumno_id):
        sesiones  = {}
        if idcurso:
            tipo = 'practica'
            alumno = self.env['leulit.alumno'].browse(alumno_id)
            sesiones = alumno.get_sesiones(idcurso)
            if sesiones:
                for sesion in sesiones:
                    result = alumno.xmlrpc_sesion_horas(alumno_id, sesion, idcurso, tipo)
                    sesiones[sesion].update({
                        'total_doblemando': result['total_doblemando'],
                        'total_pic': result['total_pic'],
                        'total_spic': result['total_spic'],
                        'total_otros': result['total_otros'],
                    })
            _logger.error("--> practicas = %r",sesiones)

        return {
            'practicas' : sesiones,
        }

    @api.onchange('rel_alumnos')
    def _onchange_rel_alumnos(self):
        """Actualiza el dominio de rel_curso según los alumnos seleccionados."""
        # Obtener IDs de alumnos desde el contexto o desde el campo
        if 'default_rel_alumnos' in self.env.context:
            alumnos_ids = self.env.context['default_rel_alumnos']
        else:
            alumnos_ids = self.rel_alumnos.ids

        if not alumnos_ids:
            # Si no hay alumnos, mostrar todos los cursos activos
            return {
                'domain': {
                    'rel_curso': [('estado', '=', 'activo')]
                }
            }

        # Verificar si algún alumno es empleado o está inactivo
        alumnos = self.env['leulit.alumno'].browse(alumnos_ids)
        alumno_employee = False
        
        for alumno in alumnos:
            if not alumno.activo:
                alumno_employee = True
                break
            # Buscar usuario asociado al alumno
            user = self.env['res.users'].search([
                ('partner_id', '=', alumno.partner_id.id)
            ], limit=1)
            if user and user.employee_id:
                alumno_employee = True
                break

        # Si hay alumnos empleados o inactivos, mostrar todos los cursos
        if alumno_employee:
            return {
                'domain': {
                    'rel_curso': [('estado', '=', 'activo')]
                }
            }

        # Obtener cursos activos asociados a los alumnos (sin fecha de finalización)
        rel_alumno_curso = self.env['leulit.rel_alumno_curso'].search([
            ('alumno_id', 'in', alumnos_ids),
            ('fecha_finalizacion', '=', False)
        ])
        cursos_ids = rel_alumno_curso.mapped('curso_id').ids

        return {
            'domain': {
                'rel_curso': [('id', 'in', cursos_ids), ('estado', '=', 'activo')]
            }
        }

    @api.onchange('rel_curso')
    def _onchange_rel_curso(self):
        """Actualiza el estado de los silabus según el curso y alumnos seleccionados."""
        if not self.rel_curso:
            return

        # Obtener IDs de alumnos
        if 'default_rel_alumnos' in self.env.context:
            alumnos_ids = self.env.context['default_rel_alumnos']
        else:
            alumnos_ids = self.rel_alumnos.ids

        if not alumnos_ids:
            return

        # Obtener todos los silabus del curso
        silabus_ids = self.env['leulit.silabus'].search([
            ('curso_id', '=', self.rel_curso.id)
        ])

        if not silabus_ids:
            return

        # Obtener silabus ya realizados por los alumnos en este curso
        # (que no tienen perfil de formación completo)
        silabus_realizados = set()
        
        for alumno_id in alumnos_ids:
            # Verificar si el alumno tiene perfil de formación para este curso
            pf_curso = self.env['leulit.perfil_formacion_curso'].search([
                ('curso', '=', self.rel_curso.id),
                ('alumno', '=', alumno_id)
            ], limit=1)
            
            if not pf_curso:
                # Obtener las relaciones curso-alumno existentes
                rel_curso_alu = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([
                    ('rel_curso', '=', self.rel_curso.id),
                    ('alumno', '=', alumno_id)
                ])
                # Agregar los silabus de estas relaciones
                silabus_realizados.update(rel_curso_alu.mapped('rel_silabus').ids)

        # Actualizar el estado de los silabus
        # NOTA: Esto modifica registros persistentes desde un TransientModel
        # Solo debería usarse si 'silabusDoit' es un campo computed o relacionado
        for silabus in silabus_ids:
            if silabus_realizados:
                silabus.silabusDoit = silabus.id in silabus_realizados
            else:
                silabus.silabusDoit = False



    def create_rel_parte_escuela_cursos_alumnos(self):
        for item in self:
            for isilabus in item.silabus:
                for alu in item.rel_alumnos:
                    parte_vals = {
                        'rel_curso'           : item.rel_curso.id,
                        'rel_silabus'         : isilabus.id,
                        'alumno'              : alu.id,
                        'rel_parte_escuela'   : item.parte_escuela_id.id,
                    }
                    self.env['leulit.rel_parte_escuela_cursos_alumnos'].create(parte_vals)

            item.parte_escuela_id.updateTiempos()


    def create_rel_parte_escuela_cursos_alumnos_vuelo(self):
        for item in self:
            for isilabus in item.silabus:
                for alu in item.rel_alumnos:
                    parte_vals = {
                        'rel_curso'           : item.rel_curso.id,
                        'rel_silabus'         : isilabus.id,
                        'alumno'              : alu.id,
                        'rel_vuelo'           : item.vuelo_id.id,
                    }
                    self.env['leulit.rel_parte_escuela_cursos_alumnos'].create(parte_vals)

        return {'type': 'ir.actions.act_window_close'}


    def _get_valoracion_options(self):
        return (
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
        )
              

    rel_curso = fields.Many2one('leulit.curso', 'Curso', required=True)
    silabus = fields.Many2many('leulit.silabus', 'leulit_silabus_rel','popup_rel','silabus_id','Silabus', required=True)
    rel_alumnos = fields.Many2many('leulit.alumno', relation='leulit_prpeca_alumno_rel', column1='popup_id', column2='alumno_id', string='Alumnos')
    tiempo = fields.Float('Tiempo dedicado (hh:mm)')
    parte_escuela_id = fields.Many2one('leulit.parte_escuela', 'Parte escuela')
    codigo_vuelo = fields.Char('Contenido')
    vuelo_id = fields.Many2one('leulit.vuelo', 'Vuelo', ondelete='set null')
    profesor_id = fields.Many2one('leulit.profesor','Profesor',ondelete='restrict')
    fecha = fields.Date('Fecha')
    hora_start = fields.Float('Hora inicio', )
    hora_end = fields.Float('Hora fin', )
    comentario = fields.Text('Comentario')
    valoracion = fields.Selection(_get_valoracion_options,'Valoración')
    search_tipo = fields.Char(string="")
    fase_vuelo = fields.Selection([('fase_1', 'Fase 1'), ('fase_2', 'Fase 2')], 'Fase de vuelo')



