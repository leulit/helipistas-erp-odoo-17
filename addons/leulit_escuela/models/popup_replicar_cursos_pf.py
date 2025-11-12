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
        _logger.info("="*80)
        _logger.info("INICIANDO metodo_popup_a_ejecutar - Replicar Cursos")
        for item in self:
            _logger.info(f"Template: {item.perfil_formacion_tmpl.name} (ID: {item.perfil_formacion_tmpl.id})")
            _logger.info(f"Total cursos en template: {len(item.perfil_formacion_tmpl.cursos)}")
            _logger.info(f"Total perfiles destino: {len(item.perfil_formacion_replica_ids)}")
            
            # bucle de cursos del template
            for idx_curso, curso_tmpl in enumerate(item.perfil_formacion_tmpl.cursos, 1):
                _logger.info(f"\n--- Procesando curso {idx_curso}/{len(item.perfil_formacion_tmpl.cursos)} ---")
                _logger.info(f"Curso template: {curso_tmpl.descripcion} (ID: {curso_tmpl.id})")
                
                # bucle de los perfiles de formacion seleccionados en el popup
                for idx_pf, pf in enumerate(item.perfil_formacion_replica_ids, 1):
                    _logger.info(f"\n  Perfil destino {idx_pf}: {pf.name} (ID: {pf.id})")
                    _logger.info(f"  Alumno: {pf.alumno.name if pf.alumno else 'SIN ALUMNO'} (ID: {pf.alumno.id if pf.alumno else 'N/A'})")
                    _logger.info(f"  Cursos actuales en perfil: {len(pf.cursos)}")
                    
                    cont = 0
                    curso_escuela = False
                    if curso_tmpl.curso:
                        curso_escuela = curso_tmpl.curso.id
                        _logger.info(f"  Curso escuela ID: {curso_escuela}")
                    
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
                    _logger.info(f"  Valores a aplicar: {curso_vals}")
                    
                    # bucle de los cursos del perfil de formacion
                    for curso_pf in pf.cursos:
                        # Si coinicide el curso que ya esta en el perfil de formacion con el curso del template solo actualiza los datos
                        # si no entra en el if el contador no suma.
                        if curso_pf.pf_curso_tmpl.id == curso_tmpl.id:
                            _logger.info(f"  ✓ Curso YA EXISTE (ID: {curso_pf.id}), actualizando con write()")
                            curso_pf.write(curso_vals)
                            cont += 1
                    
                    # si no hay ningun curso que coincida entre el perfil de formacion y el template, lo crea directamente
                    if cont == 0:
                        _logger.info(f"  ✓ Curso NO EXISTE, creando nuevo con create()")
                        # Crear el curso directamente sin usar write() para evitar reemplazar los existentes
                        pf_curso_creado = self.env['leulit.perfil_formacion_curso'].create(curso_vals)
                        _logger.info(f"  ✓ Curso creado exitosamente (ID: {pf_curso_creado.id})")
                        _logger.info(f"  - perfil_formacion: {pf_curso_creado.perfil_formacion.id if pf_curso_creado.perfil_formacion else 'NULL'}")
                        _logger.info(f"  - alumno computado: {pf_curso_creado.alumno.id if pf_curso_creado.alumno else 'NULL'}")
                        
                        # Busca si hay cursos realizados del alumno y lo realizamos con el ultimo regitro.
                        # pf_curso_creado ya está disponible, no hace falta buscarlo
                        # Buscar otros cursos del mismo alumno para copiar el historial
                        _logger.info(f"  Buscando historial de otros cursos del mismo alumno...")
                        another_pf_cursos = self.env['leulit.perfil_formacion_curso'].search([('curso','=',curso_escuela),('perfil_formacion','!=',pf.id),('alumno','=',pf.alumno.id)])
                        _logger.info(f"  Encontrados {len(another_pf_cursos)} cursos previos del alumno")
                        
                        for a_pf_curso in another_pf_cursos:
                            last_done = self.env['leulit.perfil_formacion_curso_last_done'].search([('pf_curso','=',a_pf_curso.id),('is_last','=',True)])
                            if last_done:
                                _logger.info(f"  ✓ Copiando historial last_done (ID: {last_done.id}) al nuevo curso")
                                last_done.copy(default={'pf_curso':pf_curso_creado.id})
                    else:
                        _logger.info(f"  ✓ Curso actualizado {cont} vez/veces")

        _logger.info("\n" + "="*80)
        _logger.info("FINALIZADO metodo_popup_a_ejecutar - Replicar Cursos")
        _logger.info("="*80)
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
    
