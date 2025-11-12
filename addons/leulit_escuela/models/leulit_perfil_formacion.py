# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_perfil_formacion(models.Model):
    _name = "leulit.perfil_formacion"
    _description = "leulit_perfil_formacion"
    _order = "name"

    def create_perfil_formacion_from_template(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_popup_perfil_formacion_form')
        view_id = view_ref and view_ref[1] or False
        context = {
             'default_master_id': self.id
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Perfil Formación',
            'res_model': 'leulit.popup_perfil_formacion',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }


    @api.depends('is_template','cursos')
    def _get_semaforo(self):
        for item in self:
            if item.is_template:
                item.semaforo = 'N.A.'
            else:
                pfcs = self.env['leulit.perfil_formacion_curso'].search([('id', 'in', item.cursos.ids),('finalizado', '=', False)])
                semaforo_counts = {'red': 0, 'yellow': 0, 'green': 0}

                # Contar los colores en pfcs
                for color in pfcs.mapped('semaforo_dy'):
                    if color in semaforo_counts:
                        semaforo_counts[color] += 1

                # Contar los colores en acciones_new
                for color in item.acciones_new.mapped('semaforo_dy'):
                    if color in semaforo_counts:
                        semaforo_counts[color] += 1

                # Asignar el valor de semaforo basado en las cuentas
                if semaforo_counts['red'] > 0:
                    item.semaforo = 'red'
                elif semaforo_counts['yellow'] > 0:
                    item.semaforo = 'yellow'
                elif semaforo_counts['green'] > 0:
                    item.semaforo = 'green'
                else:
                    item.semaforo = 'N.A.'


    def _store_semaforo(self):
        idspf = []
        for item in self:
            if item.perfil_formacion:
                if item.perfil_formacion.id not in idspf:
                    idspf.append(item.perfil_formacion.id)
        return idspf


    @api.depends('is_template','cursos')
    def _get_cursos_in_red(self):
        for item in self:
            if not item.is_template:
                # Buscar cursos en rojo
                ids = self.env['leulit.perfil_formacion_curso'].search([
                    ('id','in',item.cursos.ids),
                    ('semaforo_dy','=','red'),
                    ('finalizado','=',False)
                ])
                # Asignar directamente el recordset, NO una lista con el recordset dentro
                item.cursos_in_red = ids
            else:
                item.cursos_in_red = False


    def replicar_cursos(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_popup_replicar_cursos_pf_form')
        view_id = view_ref and view_ref[1] or False 
        for item in self:       
            context = {
                'default_perfil_formacion_tmpl': item.id,
            }
            return {
                    'type'           : 'ir.actions.act_window',
                    'name'           : 'Replicar Cursos Perfil Formación',
                    'res_model'      : 'leulit.popup_replicar_cursos_pf',
                    'view_mode'      : 'form',
                    'view_id'        : view_id,
                    'target'         : 'new',
                    'nodestroy'      : True,
                    'context'        : context,
            }


    def replicar_acciones(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20230125_1244_form')
        view_id = view_ref and view_ref[1] or False
        for item in self:       
            context = {
                'default_perfil_formacion_tmpl': item.id,
            }
            return {
                    'type'           : 'ir.actions.act_window',
                    'name'           : 'Replicar Acciones Perfil Formación',
                    'res_model'      : 'leulit.popup_replicar_pf_acciones',
                    'view_type'      : 'form',
                    'view_mode'      : 'form',
                    'view_id'        : view_id,
                    'target'         : 'new',
                    'nodestroy'      : True,
                    'context'        : context,
                }

    def _get_cursos_tmpl(self):
        for item in self:
            item.cursos_tmpl = item.perfil_tmpl.cursos
        
    def _get_tipos_helicoptero(self):
        return utilitylib.leulit_get_tipos_helicopteros()

    def _get_user_from_alumno(self):
        for item in self:
            item.user_id = False
            if item.alumno:
                if item.alumno.partner_id:
                    if item.alumno.partner_id.user_ids:
                        item.user_id = item.alumno.partner_id.user_ids[0]

    name = fields.Char('Nombre', required=True)
    inactivo = fields.Boolean('Inactivo', default=False)
    active = fields.Boolean(string='Activo',default=True)
    is_template = fields.Boolean('¿Es plantilla?')
    cursos = fields.One2many('leulit.perfil_formacion_curso', 'perfil_formacion', 'Perfil formación curso', domain=[('finalizado','=',False)])
    cursos_finalizados = fields.One2many('leulit.perfil_formacion_curso', 'perfil_formacion', 'Perfil formación curso', domain=[('finalizado','=',True)])
    acciones = fields.One2many('leulit.perfil_formacion_accion', 'perfil_formacion', 'Perfil formación acciones')
    perfil_tmpl = fields.Many2one('leulit.perfil_formacion', 'Perfil tmpl')
    cursos_tmpl = fields.One2many(compute=_get_cursos_tmpl,comodel_name='leulit.perfil_formacion_curso', inverse_name='perfil_formacion', string='Cursos plantilla')
    actividad_id = fields.Many2one('leulit.actividad_vuelo', 'Actividad')
    cursos_in_red = fields.One2many(compute=_get_cursos_in_red,comodel_name='leulit.perfil_formacion_curso',string='Cursos',store=False)
    semaforo = fields.Char(compute=_get_semaforo, string='')
    piloto = fields.Many2one('leulit.piloto', 'Piloto')
    alumno = fields.Many2one(comodel_name='leulit.alumno', string='Alumno')
    user_id = fields.Many2one(compute=_get_user_from_alumno ,comodel_name='res.users', string='Usuario', store=True)
    piloto_activo = fields.Selection(related='piloto.state',selection=[('activo', 'Activo'), ('baja', 'Baja')],string='Estado piloto')
    perfil_formacion_id = fields.Many2one('leulit.perfil_formacion', 'Perfil Formacion')
    perfil_formacion_accion_id = fields.Many2one('leulit.perfil_formacion', 'Perfil Formacion')
    acciones_new = fields.One2many('leulit.pf_accion', 'perfil_formacion', 'Perfil formación acciones')
    tipo_helicoptero_tmpl = fields.Selection(_get_tipos_helicoptero, string='Modelo Helicoptero')
    vuelo_tipo_id_tmpl = fields.Many2one(comodel_name='leulit.vuelostipo', string='Tipo vuelo')
    tipo_helicoptero = fields.Selection(related='perfil_tmpl.tipo_helicoptero_tmpl', string='Modelo Helicoptero')
    vuelo_tipo_id = fields.Many2one(related='perfil_tmpl.vuelo_tipo_id_tmpl', comodel_name='leulit.vuelostipo', string='Tipo vuelo')
    operador_tmpl = fields.Boolean(string='Personal especialista')
    operador = fields.Boolean(related='perfil_tmpl.operador_tmpl',string='Personal especialista')
    water_zone_tmpl = fields.Boolean(string='Operaciones sobre agua')
    water_zone = fields.Boolean(related='perfil_tmpl.water_zone_tmpl',string='Operaciones sobre agua')
    is_piloto_externo = fields.Boolean(string='Piloto externo')

    _sql_constraints = [("alumno_perfil_unique", "UNIQUE(alumno,perfil_tmpl)", "Ya existe un perfil con este alumno")]


    def archivar_perfil_formacion(self):
        return self.write({'inactivo': True})

    def activar_perfil_formacion(self):
        return self.write({'inactivo': False})

    def copy_cursos_hechos(self):
        for item in self:
            for curso in item.cursos:
                cursos_others = self.env['leulit.perfil_formacion_curso'].search([('id','!=',curso.id),('curso','=',curso.curso.id),('alumno','=',curso.alumno.id)],order='id desc')
                for curso_others in cursos_others:
                    if curso_others:
                        if curso_others.last_done_history:
                            last_done_last_curso = sorted(curso_others.last_done_history, key=lambda x: x.done_date or datetime.min)[-1]
                            last_done_last_curso.copy(default={'pf_curso': curso.id})
                            break
            for accion in item.acciones_new:
                acciones_others = self.env['leulit.pf_accion'].search([('id','!=',accion.id),('accion','=',accion.accion.id),('alumno','=',accion.alumno.id)],order='id desc')
                for accion_others in acciones_others:
                    if accion_others:
                        if accion_others.realizados_last_done:
                            last_done_last_accion = sorted(accion_others.realizados_last_done, key=lambda x: x.done_date or datetime.min)[-1]
                            last_done_last_accion.copy(default={'pf_accion': accion.id})
                            break
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def imprimir_perfil_formacion(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20211015_1231_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_perfil_formacion': self.id,
        }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Imprimir partes pérfil formación',
            'res_model': 'leulit.perfil_formacion_print_wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }