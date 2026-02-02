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

    @api.model
    def default_get(self, fields_list):
        try:
            _logger.info(
                "[Escuela] default_get for popup: fields=%s ctx_defaults=%s",
                fields_list,
                {k: v for k, v in self.env.context.items() if k.startswith('default_')},
            )
        except Exception:
            _logger.exception("[Escuela] Error logging wizard default_get inputs")

        defaults = super(leulit_popup_rel_parte_escuela_cursos_alumnos, self).default_get(fields_list)
        try:
            _logger.info(
                "[Escuela] default_get result: rel_alumnos=%s rel_curso=%s profesor_id=%s",
                defaults.get('rel_alumnos'),
                defaults.get('rel_curso'),
                defaults.get('profesor_id'),
            )
        except Exception:
            _logger.exception("[Escuela] Error logging wizard default_get result")
        return defaults
    @api.model
    def create(self, vals):
        # Log de creación del wizard con valores de entrada
        try:
            ctx_min = {k: v for k, v in self.env.context.items() if k.startswith('default_') or k in ('lang', 'tz')}
            _logger.info(
                "[Escuela] Creating popup wizard by user=%s ctx=%s vals=%s",
                self.env.user.id,
                ctx_min,
                vals,
            )
        except Exception:
            _logger.exception("[Escuela] Error logging wizard create inputs")

        rec = super(leulit_popup_rel_parte_escuela_cursos_alumnos, self).create(vals)

        try:
            _logger.info(
                "[Escuela] Created popup wizard id=%s rel_curso=%s profesor_id=%s rel_alumnos=%s silabus=%s",
                rec.id,
                rec.rel_curso.id if rec.rel_curso else None,
                rec.profesor_id.id if rec.profesor_id else None,
                rec.rel_alumnos.ids,
                rec.silabus.ids,
            )
        except Exception:
            _logger.exception("[Escuela] Error logging wizard create state")

        return rec

    def write(self, vals):
        try:
            _logger.info(
                "[Escuela] Writing popup wizard ids=%s vals=%s",
                self.ids,
                vals,
            )
        except Exception:
            _logger.exception("[Escuela] Error logging wizard write inputs")

        res = super(leulit_popup_rel_parte_escuela_cursos_alumnos, self).write(vals)
        try:
            _logger.info(
                "[Escuela] Post-write state wizard ids=%s rel_curso=%s profesor_id=%s rel_alumnos=%s silabus=%s",
                self.ids,
                [r.rel_curso.id if r.rel_curso else None for r in self],
                [r.profesor_id.id if r.profesor_id else None for r in self],
                [r.rel_alumnos.ids for r in self],
                [r.silabus.ids for r in self],
            )
        except Exception:
            _logger.exception("[Escuela] Error logging wizard post-write state")
        return res

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
        try:
            _logger.info(
                "[Escuela] onchange_colores triggered: rel_curso=%s rel_alumnos_ctx=%s rel_alumnos_field=%s",
                self.rel_curso.id if self.rel_curso else None,
                self.env.context.get('default_rel_alumnos'),
                self.rel_alumnos.ids,
            )
        except Exception:
            _logger.exception("[Escuela] Error logging onchange_colores inputs")
        
        RelCursoAlu  = self.env['leulit.rel_parte_escuela_cursos_alumnos']
        Silabus      = self.env['leulit.silabus']
        PFCurso      = self.env['leulit.perfil_formacion_curso']
        Alumno       = self.env['leulit.alumno']
        Curso        = self.env['leulit.curso']
        RelAlumnoCurso = self.env['leulit.rel_alumno_curso']
        
        objAllSilabus_ids = []
        objSilabus = []

        # Normalizar alumnos desde contexto por si viene como comando M2M (6, 0, ids)
        if 'default_rel_alumnos' in self.env.context:
            alumnos_ctx = self.env.context['default_rel_alumnos']
            alumnos = []
            if isinstance(alumnos_ctx, list):
                if alumnos_ctx and isinstance(alumnos_ctx[0], int):
                    alumnos = alumnos_ctx
                else:
                    for cmd in alumnos_ctx:
                        if isinstance(cmd, (tuple, list)) and cmd and cmd[0] == 6 and len(cmd) >= 3:
                            ids = cmd[2] if isinstance(cmd[2], list) else []
                            alumnos.extend(ids)
            elif isinstance(alumnos_ctx, int):
                alumnos = [alumnos_ctx]
        else:
            alumnos = self.rel_alumnos.ids

        # Marcar sílabus ya utilizados
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

        # Determinar si hay alumnos empleados/inactivos (una sola búsqueda)
        alumno_employee = False
        if alumnos:
            alumnos_objs = Alumno.search([('id','in',alumnos)])
            for alumno in alumnos_objs:
                user = self.env['res.users'].search([('partner_id','=',alumno.partner_id.id)], limit=1)
                if user.employee_id or alumno.activo == False:
                    alumno_employee = True
                    break

        # === LÓGICA DE FILTRADO BIDIRECCIONAL ===
        cursos_ids = Curso.search([('estado', '=', 'activo')]).ids
        alumnos_ids = []
        
        # CASO 1: Hay alumnos seleccionados → filtrar cursos
        if alumnos:
            if alumno_employee:
                # Si es empleado activo → todos los cursos activos
                cursos_ids = Curso.search([('estado', '=', 'activo')]).ids
            else:
                # Si NO es empleado → solo cursos asignados sin finalizar
                cursos_ids = RelAlumnoCurso.search([
                    ('alumno_id', 'in', alumnos),
                    ('fecha_finalizacion', '=', False)
                ]).mapped('curso_id').filtered(lambda c: c.estado == 'activo').ids
        
        # CASO 2: Hay curso seleccionado → filtrar alumnos
        if self.rel_curso:
            if self.rel_curso.ato_mi:
                # Si el curso tiene ATO MI → solo alumnos con ese curso asignado sin finalizar
                alumnos_ids = RelAlumnoCurso.search([
                    ('curso_id', '=', self.rel_curso.id),
                    ('fecha_finalizacion', '=', False)
                ]).mapped('alumno_id').ids
            else:
                # Si NO tiene ATO MI → todos los alumnos del sistema
                alumnos_ids = Alumno.search([]).ids
            
            # Si no hay alumnos seleccionados, mantener todos los cursos activos
            if not alumnos:
                cursos_ids = Curso.search([('estado', '=', 'activo')]).ids

        try:
            _logger.info(
                "[Escuela] onchange_colores domains computed: cursos_ids=%s alumnos_ids=%s",
                cursos_ids,
                alumnos_ids,
            )
        except Exception:
            _logger.exception("[Escuela] Error logging onchange_colores domains")

        self.cursos_domain_ids = [(6, 0, cursos_ids)]
        self.alumnos_domain_ids = [(6, 0, alumnos_ids)]

        return {
            'domain': {
                'rel_curso': [('id', 'in', cursos_ids if cursos_ids else []), ('estado', '=', 'activo')],
                'rel_alumnos': [('id', 'in', alumnos_ids)] if alumnos_ids else []
            }
        }



    def create_rel_parte_escuela_cursos_alumnos(self):
        for item in self:
            try:
                _logger.info(
                    "[Escuela] create_rel_parte_escuela_cursos_alumnos: parte_escuela_id=%s rel_curso=%s alumnos=%s silabus=%s",
                    item.parte_escuela_id.id if item.parte_escuela_id else None,
                    item.rel_curso.id if item.rel_curso else None,
                    item.rel_alumnos.ids,
                    item.silabus.ids,
                )
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
            except Exception:
                _logger.exception("[Escuela] Error in create_rel_parte_escuela_cursos_alumnos")
                raise


    def create_rel_parte_escuela_cursos_alumnos_vuelo(self):
        for item in self:
            try:
                _logger.info(
                    "[Escuela] create_rel_parte_escuela_cursos_alumnos_vuelo: vuelo_id=%s rel_curso=%s alumnos=%s silabus=%s",
                    item.vuelo_id.id if item.vuelo_id else None,
                    item.rel_curso.id if item.rel_curso else None,
                    item.rel_alumnos.ids,
                    item.silabus.ids,
                )
                for isilabus in item.silabus:
                    for alu in item.rel_alumnos:
                        parte_vals = {
                            'rel_curso'           : item.rel_curso.id,
                            'rel_silabus'         : isilabus.id,
                            'alumno'              : alu.id,
                            'rel_vuelo'           : item.vuelo_id.id,
                        }
                        self.env['leulit.rel_parte_escuela_cursos_alumnos'].create(parte_vals)
            except Exception:
                _logger.exception("[Escuela] Error in create_rel_parte_escuela_cursos_alumnos_vuelo")
                raise

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
    cursos_domain_ids = fields.Many2many('leulit.curso', string='Cursos dominio', readonly=True)
    alumnos_domain_ids = fields.Many2many('leulit.alumno', string='Alumnos dominio', readonly=True)



