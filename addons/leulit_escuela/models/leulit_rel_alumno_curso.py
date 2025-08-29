# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_rel_alumno_curso(models.Model):
    _name = "leulit.rel_alumno_curso"
    _description = "leulit_rel_alumno_curso"
    

    def informe_cursos_alu(self):
    #     data = self.read(cr, uid, ids, context)[-1]
    #     return {
    #         'type': 'ir.actions.report.xml',
    #         'report_name': 'leulit_informe_cursos_alu',
    #         'datas': {
    #             'model': 'leulit.alumno',
    #             'ids': ids,
    #             'report_type': "pdf",
    #             'form': data
    #         },
    #         'nodestroy': False
    #     }
        raise UserError('Funcionalidad no migrada boton')


    @api.depends('alumno_id')
    def _get_cursos_perfil_formacion(self):
        for item in self:
            pf_cursos = False
            if item.alumno_id.piloto_id and len(item.alumno_id.piloto_id) > 0:
                pf_cursos = self.env['leulit.perfil_formacion_curso'].search([('curso', '=', item.curso_id.id), ('piloto', '=', item.alumno_id.piloto_id.id)])
            if not pf_cursos:
                item.cursos_perfil_formacion = False
            else:
                item.cursos_perfil_formacion = True


    def _search_cursos_perfil_formacion(self, operator, value):
        ids = []
        for item in self.search([]):
            pf_cursos = False
            if item.alumno_id.piloto_id and len(item.alumno_id.piloto_id) > 0:
                pf_cursos = self.env['leulit.perfil_formacion_curso'].search([('curso', '=', item.curso_id.id), ('piloto', '=', item.alumno_id.piloto_id.id)])
            if not pf_cursos:
                ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]


    curso_id = fields.Many2one('leulit.curso', 'Curso', required=True, domain=[('estado','=','activo'),('is_curso_pf','=',False)])
    alumno_id = fields.Many2one('leulit.alumno', 'Alumno', required=True)
    alumno_name = fields.Char(related='alumno_id.name',string='Nombre')
    fecha_inscripcion = fields.Date("Fecha de inicio", required=True)
    fecha_finalizacion = fields.Date("Fecha de finalización")
    comentarios = fields.Text('Comentarios')
    cursos_perfil_formacion = fields.Boolean(compute='_get_cursos_perfil_formacion', string='Cursos perfil formación',store=False, search=_search_cursos_perfil_formacion)


    def get_alumnos_activos(self,period_end,period_start):
        lista = []
        items = self.search([])
        for item in items:
            if item.fecha_inscripcion <= period_end:
                if item.fecha_finalizacion >= period_start or fecha_finalizacion == False:
                    if item.alumno_id.id not in lista:
                        lista.append(item.alumno_id.id)
        return len(lista)
