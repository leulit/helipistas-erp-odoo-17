# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class leulit_rel_parte_escuela_cursos_alumnos(models.Model):
    _name           = "leulit.rel_parte_escuela_cursos_alumnos"
    _description    = "leulit_rel_parte_escuela_cursos_alumnos"
    
    def verificar_alumno(self):
        for item in self:
            item.write({'verificado': True, 'verificado_por': self.env.uid})
    
    def add_docs_rel_parte_escuela(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20211111_1256_form')
        view_id = view_ref and view_ref[1] or False

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Añadir Documento Silabus',
           'res_model'      : 'leulit.rel_parte_escuela_cursos_alumnos',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'res_id'         : self.id,
            'flags'         : {'form': {'action_buttons': True}}
        }
    
    def _get_valoracion_options(self):
        return (
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
            ('apto', 'Apto'),
            ('noapto', 'No Apto'),
        )

    def verficar_por_orden(self):
        for item in self:
            if not item.verificado:
                item.verificado = True
                item.verificado_por = self.env.uid

    @api.depends('valoracion','rel_docs','nota')
    def _get_todo_cerrar(self):
        for item in self:
            item.todo_cerrar = False
            if item.sil_valoracion and item.valoracion == False:
                item.todo_cerrar = True
            if item.sil_test:
                if len(item.rel_docs.ids) == 0 or item.nota == -1:
                    item.todo_cerrar =  True


    rel_curso = fields.Many2one('leulit.curso', 'Curso', required=True)
    ato = fields.Boolean(related='rel_curso.ato_mi',string="ATO")
    rel_silabus = fields.Many2one('leulit.silabus', 'Silabus', required=True)
    asignatura = fields.Char(related='rel_silabus.asignatura_id.descripcion',string='Asignatura')
    duracion = fields.Float(related='rel_silabus.duracion',string="Tiempo teórico")
    rel_alumnos = fields.Many2one('leulit.piloto', 'Alumno', required=False)
    alumno = fields.Many2one('leulit.alumno', 'Alumno', required=False)
    rel_vuelo = fields.Many2one(comodel_name='leulit.vuelo', string='Parte de Vuelo', ondelete="cascade")
    rel_parte_escuela = fields.Many2one('leulit.parte_escuela', 'Parte escuela', required=False, ondelete="set null")
    parte_escuela_id = fields.Integer(related='rel_parte_escuela.id',string='Id del Parte',store=False)
    fecha = fields.Date(related='rel_parte_escuela.fecha',string="Fecha",store=True)
    estado = fields.Selection(related='rel_parte_escuela.estado',string="Estado")
    profesor_id = fields.Many2one(related='rel_parte_escuela.profesor', string="Profesor", comodel_name="leulit.profesor", store=True)
    firma_profesor_id = fields.Binary(related='rel_parte_escuela.profesor.firma', string="Firma Profesor")
    tiempo = fields.Float('Tiempo dedicado',)
    tiempo_total = fields.Float('Tiempo total', default=0)
    verificado = fields.Boolean('Verificado')
    sil_test = fields.Boolean(related='rel_silabus.test',string='TEST')
    rel_docs = fields.One2many(comodel_name='ir.attachment', inverse_name='rel_parte_escuela', string='Documentos')
    valoracion = fields.Selection(_get_valoracion_options,'Valoración')
    comentario = fields.Text('Comentario')
    fechaparte = fields.Date(related='rel_parte_escuela.fecha',string='Fecha Parte',store=False)
    verificado_por = fields.Many2one('res.users', 'Verificado por', readonly=True)
    nota = fields.Integer(string="Nota %",default=-1)
    sil_valoracion = fields.Boolean(related='rel_silabus.valoracion',string='Valoración')
    todo_cerrar = fields.Boolean(compute=_get_todo_cerrar, string="ToDo Cerrar")



    def get_partes_alumno_by_curso_and_silabus_fechas(self, alumno, curso, silabus, fecha_inicio, fecha_fin):
        if fecha_inicio:
            sql = "SELECT leulit_rel_parte_escuela_cursos_alumnos.id " \
                "FROM leulit_rel_parte_escuela_cursos_alumnos JOIN leulit_parte_teorica ON " \
                "leulit_rel_parte_escuela_cursos_alumnos.rel_parte_escuela = leulit_parte_teorica.id " \
                "WHERE " \
                "leulit_parte_teorica.estado = 'cerrado' AND " \
                "leulit_rel_parte_escuela_cursos_alumnos.rel_curso = {0} AND " \
                "leulit_rel_parte_escuela_cursos_alumnos.alumno = {1} AND " \
                "leulit_rel_parte_escuela_cursos_alumnos.rel_silabus = {2} AND " \
                "leulit_parte_teorica.fecha::DATE > '{3}'::DATE AND " \
                "leulit_parte_teorica.fecha::DATE <= '{4}'::DATE " \
                "ORDER BY leulit_parte_teorica.fecha DESC " \
                "".format(curso, alumno, silabus, fecha_inicio, fecha_fin)
            self._cr.execute(sql)
            rows = self._cr.fetchall()
            ids_informe = [x[0] for x in rows]
            return ids_informe
        else:
            sql = "SELECT leulit_rel_parte_escuela_cursos_alumnos.id " \
                "FROM leulit_rel_parte_escuela_cursos_alumnos JOIN leulit_parte_teorica ON " \
                "leulit_rel_parte_escuela_cursos_alumnos.rel_parte_escuela = leulit_parte_teorica.id " \
                "WHERE " \
                "leulit_parte_teorica.estado = 'cerrado' AND " \
                "leulit_rel_parte_escuela_cursos_alumnos.rel_curso = {0} AND " \
                "leulit_rel_parte_escuela_cursos_alumnos.alumno = {1} AND " \
                "leulit_rel_parte_escuela_cursos_alumnos.rel_silabus = {2} AND " \
                "leulit_parte_teorica.fecha::DATE <= '{3}'::DATE " \
                "ORDER BY leulit_parte_teorica.fecha DESC " \
                "".format(curso, alumno, silabus, fecha_fin)
            self._cr.execute(sql)
            rows = self._cr.fetchall()
            ids_informe = [x[0] for x in rows]
            return ids_informe

    

    def upd_set_rel_vuelo(self):
        _logger.error("################### upd_set_rel_vuelo ")
        threaded_calculation = threading.Thread(target=self.run_upd_set_rel_vuelo, args=([]))
        _logger.error("################### upd_set_rel_vuelo start thread")
        threaded_calculation.start()

    def run_upd_set_rel_vuelo(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            for item in self.search([]):
                if item.rel_parte_escuela:
                    if item.rel_parte_escuela.vuelo_id:
                        item.rel_vuelo = item.rel_parte_escuela.vuelo_id.id

            _logger.error("upd_compute_fields end thread")
            self.env.cr.commit()
