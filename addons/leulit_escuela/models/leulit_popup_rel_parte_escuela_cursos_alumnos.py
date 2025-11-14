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

    @api.onchange('rel_alumnos','rel_curso')
    def onchange_colores(self):
        RelCursoAlu  = self.env['leulit.rel_parte_escuela_cursos_alumnos']
        Silabus      = self.env['leulit.silabus']
        PFCurso      = self.env['leulit.perfil_formacion_curso']
        
        objAllSilabus_ids = []
        objSilabus = []

        if 'default_rel_alumnos' in self.env.context:
            alumnos = self.env.context['default_rel_alumnos']
        else:
            alumnos = self.rel_alumnos.ids

        if alumnos and self.rel_curso:
            objAllSilabus_ids = Silabus.search([('curso_id','=',self.rel_curso.id)])
            for alumno in alumnos:
                objPFCurso = PFCurso.search([('curso','=',self.rel_curso.id),('alumno','=',alumno)])
                if not objPFCurso:
                    objRelCursoAlu = RelCursoAlu.search([('rel_curso','=',self.rel_curso.id),('alumno','=',alumno)])
                    for relCursoAlu in objRelCursoAlu:
                        if relCursoAlu.rel_silabus.id not in objSilabus:
                            objSilabus.append(relCursoAlu.rel_silabus.id)
            if objSilabus:
                for rec_silabus in objAllSilabus_ids:
                    if rec_silabus.id in objSilabus:
                        rec_silabus.silabusDoit = True
                    else:
                        rec_silabus.silabusDoit = False
            else:
                for rec_silabus in objAllSilabus_ids:
                    rec_silabus.silabusDoit = False

        alumno_employee = False
        for alumno in self.env['leulit.alumno'].search([('id','in',alumnos)]):
            user = self.env['res.users'].search([('partner_id','=',alumno.partner_id.id)])
            if user.employee_id or alumno.activo == False:
                alumno_employee = True


        cursos_ids = self.env['leulit.curso'].search([('estado','=','activo')]).ids
        if not self.rel_curso and not alumno_employee:
            cursos_ids = []
            for curso in self.env['leulit.curso'].search([]):
                for obj_rel in self.env['leulit.rel_alumno_curso'].search([('alumno_id','in',alumnos),('curso_id','=',curso.id),('fecha_finalizacion','=',False)]):
                    cursos_ids.append(obj_rel.curso_id.id)
        return {'domain':{'rel_curso':[('id','in',cursos_ids),('estado','=','activo')]}}



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



