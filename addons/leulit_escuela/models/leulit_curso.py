# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class leulit_curso(models.Model):
    _name           = "leulit.curso"
    _description    = "leulit_curso"
    _rec_name       = "name"

    # @api.depends('name', 'revision')
    # def name_get(self):
    #     res = []
    #     for item in self:
    #         res.append((item.id, '(%s) %s' % (item.name, item.revision)))
    #     return res

    def _get_silabus_teoria(self):
        for item in self:
            item.silabus_teorico_ids = self.env['leulit.silabus'].search([('curso_id','=',item.id),('tipo','=','teorica')])

    def _get_silabus_practica(self):
        for item in self:
            item.silabus_practico_ids = self.env['leulit.silabus'].search([('curso_id','=',item.id),('tipo','=','practica')])

    @api.depends('silabus_ids')
    def _get_total_horas(self):
        for obj in self:
            obj.total_horas = sum(o2m.duracion for o2m in obj.silabus_ids)
    
    @api.depends('silabus_practico_ids')
    def _get_total_horas_practica(self):
        for obj in self:
            obj.total_horas_practico = sum(o2m.duracion for o2m in obj.silabus_practico_ids)

    @api.depends('silabus_teorico_ids')
    def _get_total_horas_teorica(self):
        for obj in self:
            obj.total_horas_teorico = sum(o2m.duracion for o2m in obj.silabus_teorico_ids)
    
    def on_change_activo(self):
        self.estado = 'activo'

    def on_change_inactivo(self):
        self.estado = 'inactivo'

    def imprimir_checklist(self):
        return self.env.ref('leulit_escuela.report_checklist_curso').report_action([])
        
    def _get_asignaturas(self):
        for item in self:
            idsSilabus = self.env['leulit.silabus'].search([('curso_id','=',item.id)])
            result = []
            for item2 in idsSilabus:
                if item2.asignatura_id  and item2.asignatura_id.id not in result:
                    result.append(item2.asignatura_id.id)
            if result:
                item.asignatura_ids = result
            else:
                item.asignatura_ids = None
    
    def _get_tiempo(self):
        for item in self:
            idspartes = self.env['leulit.parte_escuela'].search([('cursos','=',item.id),('estado','=','cerrado')])
            valor = sum(o2m.tiempo for o2m in idspartes)
            item.tiempo = valor
    
    def _get_is_curso_pf(self):
        for item in self:
            item.is_curso_pf = False
            curso_pf = self.env['leulit.perfil_formacion_curso'].search([('curso','=',item.id)])
            if curso_pf:
                item.is_curso_pf = True

    def _search_cursos_perfil_formacion(self, operator, value):
        ids = []
        for item in self.search([]):
            curso_pf = self.env['leulit.perfil_formacion_curso'].search([('curso','=',item.id)])
            if operator == '=' and value == False:
                if not curso_pf:
                    ids.append(item.id)
            if operator == '=' and value == True:
                if curso_pf:
                    ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]

    def _get_horas_by_tipo_alumno_curso(self, idalumno, idcurso, tipo):
        tiempo = 0
        for item in self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('alumno','=',idalumno),('rel_curso','=',idcurso)]):
            if item.rel_silabus.tipo == tipo:
                tiempo += item.tiempo
        return tiempo

    def _curso_ato(self):
        sql = " SELECT id FROM leulit_curso WHERE ato_mi = True"
        self._cr.execute(sql)
        rows = self._cr.fetchall()
        ids = [x[0] for x in rows]
        return ids

    def copy(self, default=None):
        default = default or {}
        new_curso = super(leulit_curso, self).copy(default)
        for silabus in self.silabus_ids:
            silabus.copy(default={'curso_id': new_curso.id})
        return new_curso

    def action_open_revision(self):
        return {
            'name': _('Abrir Revision'),
            'type': 'ir.actions.act_window',
            'res_model': 'leulit.curso',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'res_id': self.id,
        }

    def _get_logo_hlp(self):
        for item in self:
            item.logo_reports = False
            company_helipistas = self.env['res.company'].search([('name','like','Helipistas')])
            if company_helipistas:
                item.logo_reports = company_helipistas.logo_reports

    template_id = fields.Many2one(comodel_name='leulit.curso_template', string='Curso')
    name = fields.Char(string='Descripción', required=True)
    revision = fields.Char(string='Revisión')
    edicion = fields.Char(string='Edición')
    comentario = fields.Text(string='Comentario')
    silabus_ids = fields.One2many(comodel_name='leulit.silabus',inverse_name='curso_id', string='Silabus')
    silabus_teorico_ids = fields.One2many(compute=_get_silabus_teoria, comodel_name="leulit.silabus",  string="Silabus teórico")
    silabus_practico_ids = fields.One2many(compute=_get_silabus_practica, comodel_name="leulit.silabus",  string="Silabus práctico")
    total_horas = fields.Float(compute=_get_total_horas, string="Total horas")
    total_horas_practico = fields.Float(compute=_get_total_horas_practica, string="Total horas práctico")
    total_horas_teorico = fields.Float(compute=_get_total_horas_teorica, string="Total horas teórico")
    tipotitulacion = fields.Selection([('habilitacion','Habilitación'),('nuevalicencia','Nueva licencia'),], string="Tipo titulación")
    asignatura_ids = fields.One2many(compute=_get_asignaturas, comodel_name="leulit.asignatura",  string="Asignaturas", store=False)
    estado = fields.Selection([('activo','Activo'),('inactivo','Inactivo')], string='Estado',default='inactivo')
    tiempo = fields.Float(compute=_get_tiempo, string="Horas impartidas", store=False)
    ato_mo = fields.Boolean('ATO MO')
    ato_mi = fields.Boolean('ATO MI')
    nco = fields.Boolean('NCO')
    aoc = fields.Boolean('AOC')
    ttaa = fields.Boolean('TTAA')
    lci = fields.Boolean('LCI')
    camo = fields.Boolean('CAMO')
    p_145 = fields.Boolean('Parte 145')
    is_curso_pf = fields.Boolean(compute=_get_is_curso_pf, string="Es curso de perfil de formación", store=False, search=_search_cursos_perfil_formacion)
    logo_reports = fields.Binary(compute=_get_logo_hlp, string="Logo para informes")

    def print_progreso_alumnos_activos(self):
        data = self._get_data_to_print_progreso_alumnos_activos()
        return self.env.ref('leulit_escuela.leulit_20230927_1657_report').report_action(self, data=data)
    
    def _get_data_to_print_progreso_alumnos_activos(self):
        data = {}
        alumnos = []
        for alumno_curso in  self.env["leulit.rel_alumno_curso"].search([('curso_id','=',self.id),('fecha_finalizacion','=',False)]):
            alumnos.append(alumno_curso.alumno_id)
        alumnos_tablas = {}
        for alumno in alumnos:
            result = alumno.xmlrpc_asignaturas(self.id, 'teorica')
            alumnos_tablas[alumno.name] = result
        data = {
            'name' : self.name,
            'alumnos' : alumnos_tablas,
        }
        return data