# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_perfil_formacion_curso(models.Model):
    _name = "leulit.perfil_formacion_curso"
    _description = "leulit_perfil_formacion_curso"
    _rec_name = "descripcion"
    _order = "descripcion"


    def _calculateNextDoneDate(self,periodicidad_dy,last_done_date):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        result = None
        if periodicidad_dy == 0:
            result = None
        else:
            if last_done_date:
                ldd = utilitylib.endMonth(last_done_date, False)
                end_date = ldd + timedelta(days=periodicidad_dy)
                end_date = utilitylib.endMonth(end_date, False)
                result = end_date.strftime(DATE_FORMAT)
            else:
                result = None
        return result


    @api.depends('periodicidad_dy','last_done_date')
    def _get_next_done_date(self):
        for item in self:            
            item.next_done_date = item._calculateNextDoneDate(item.periodicidad_dy, item.last_done_date)


    def calc_remainder_dy(self, fecha):
        hoy = datetime.now().date()
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        ndd = fecha
        diasrestantes = (ndd - hoy).days
        return diasrestantes


    @api.depends('next_done_date')
    def _get_remainder_dy(self):
        for item in self:
            item.remainder_dy = 0
            if item.next_done_date:
                item.remainder_dy = item.calc_remainder_dy(item.next_done_date)


    def calc_semaforo_remainder_dy(self, remainder_dy, marge_dy):
        if remainder_dy <= 0:
            color = 'red'
        else:
            if remainder_dy < marge_dy:
                color = 'yellow'
            else:
                color = 'green'
        return color


    @api.depends('finalizado','remainder_dy','marge_dy')
    def _get_semaforo_dy(self):
        for item in self:
            if item.finalizado:
                item.semaforo_dy = 'N.A.'
            else:
                item.semaforo_dy = self.calc_semaforo_remainder_dy(item.remainder_dy, item.marge_dy)


    def end_course(self):
        self.write({'finalizado':True})


    def end_course_template(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20230303_1152_form')
        view_id = view_ref and view_ref[1] or False
        context = {
            'default_pf_curso': self.id,
            'default_perfil_formacion_tmpl': self.perfil_formacion.id,
        }
        return {
                'type'           : 'ir.actions.act_window',
                'name'           : 'Finalizar Curso Perfil Formación',
                'res_model'      : 'leulit.popup_replicar_cursos_pf',
                'view_mode'      : 'form',
                'view_id'        : view_id,
                'target'         : 'new',
                'nodestroy'      : True,
                'context'        : context,
        }


    def start_course(self):
        self.write({'finalizado':False})


    def start_course_template(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20230303_1200_form')
        view_id = view_ref and view_ref[1] or False 
        context = {
            'default_pf_curso': self.id,
            'default_perfil_formacion_tmpl': self.perfil_formacion.id,
        }
        return {
                'type'           : 'ir.actions.act_window',
                'name'           : 'Reiniciar Curso Perfil Formación',
                'res_model'      : 'leulit.popup_replicar_cursos_pf',
                'view_mode'      : 'form',
                'view_id'        : view_id,
                'target'         : 'new',
                'nodestroy'      : True,
                'context'        : context,
        }
    
    
    def replicar_curso_to_perfiles(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20230307_1038_form')
        view_id = view_ref and view_ref[1] or False 
        context = {
            'default_pf_curso': self.id,
            'default_perfil_formacion_tmpl': self.perfil_formacion.id,
        }
        return {
                'type'           : 'ir.actions.act_window',
                'name'           : 'Replicar Curso Perfil Formación',
                'res_model'      : 'leulit.popup_replicar_cursos_pf',
                'view_mode'      : 'form',
                'view_id'        : view_id,
                'target'         : 'new',
                'nodestroy'      : True,
                'context'        : context,
        }


    def done_course(self):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_perfil_formacion_done_course_form')
        view_id = view_ref and view_ref[1] or False
        result = False
        nitems = 0
        context = {}
        ## Recorremos la relación para encontrar los partes por alumno y curso.
        for item in self:
            if item.last_done_date:
                if ((item.alumno) and (item.curso)):
                    rel_partes_search = self.env["leulit.rel_parte_escuela_cursos_alumnos"].search([('rel_alumnos', '=', item.alumno.id),('rel_curso', '=', item.curso.id)])
            ## Buscamos los partes de escuela
                    for rel_parte in rel_partes_search:
                        if rel_parte.rel_parte_escuela:
            ## Verificamos si el parte es correcto
                            if rel_parte.rel_parte_escuela.estado == 'cerrado' and rel_parte.rel_parte_escuela.silverificado == 'cerrado_y_validado' and rel_parte.rel_parte_escuela.fecha > item.last_done_date:
                                result = True
                                nitems = nitems + 1

            context['default_pf_curso'] = item.id
            context['default_name'] = item.descripcion
            context['default_done_date'] = datetime.now().strftime(DATE_FORMAT)

        if not result and nitems > 0:
            raise  UserError(_('Invalid Action!'), _('No existe ningún parte cerrado y verificado para este curso'))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Marcar curso como realizado',
            'res_model': 'leulit.perfil_formacion_curso_last_done',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    

    def print_last_informe_general_cursos_alu_ld(self):
            last = False
            for item in self.last_done_history:
                if item.is_last:
                    last = item
            if last:
                data = last.getdata_informe_general_cursos_alu_ld()
                return self.env.ref('leulit_escuela.report_curso_pf').report_action(self,data=data)
            else:
                raise UserError("No hay registros en el Histórico del curso.")

     
    @api.onchange('curso')
    def onchange_curso(self):
        if self.curso:
            self.descripcion = self.curso.name


    @api.depends('last_done_date','piloto','curso')
    def _last_parte(self):
        for item in self:
            last_fecha = False
            if item.last_done_date:
                partes = self.env["leulit.rel_parte_escuela_cursos_alumnos"].search([('alumno', '=', item.alumno.id),('rel_curso', '=', item.curso.id)])
                for parte in partes:
                    parte_escuela = parte.rel_parte_escuela
                    if parte_escuela.estado == 'cerrado' and parte_escuela.fecha <= item.last_done_date:
                        if not last_fecha or parte_escuela.fecha > last_fecha:
                            last_fecha = parte_escuela.fecha
            item.last_parte = last_fecha


    @api.depends('last_done_date','piloto','curso')
    def _last_parte_id(self):
        for item in self:
            last_fecha = False
            last_id = False
            if item.last_done_date:
                parte_search = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('alumno', '=', item.alumno.id),('rel_curso', '=', item.curso.id)])
                for item2 in parte_search:
                    parte = item2.rel_parte_escuela
                    if parte.estado == 'cerrado' and parte.fecha <= item.last_done_date:
                        if not last_fecha or parte.fecha > last_fecha:
                            last_fecha = parte.fecha
                            last_id = parte.id
            item.last_parte_id = last_id

    
    def _search_remainder_dy(self, operator, value):
        ids = []
        for item in self.search([]):
            if item.next_done_date:
                remainder_dy = item.calc_remainder_dy(item.next_done_date)
                if operator == '=':
                    if remainder_dy == value:
                        ids.append(item.id)
                if operator == '<=':
                    if remainder_dy <= value:
                        ids.append(item.id)
                if operator == '<':
                    if remainder_dy < value:
                        ids.append(item.id)
                if operator == '>=':
                    if remainder_dy >= value:
                        ids.append(item.id)
                if operator == '>':
                    if remainder_dy > value:
                        ids.append(item.id)
                if operator == '!=':
                    if remainder_dy != value:
                        ids.append(item.id)

        if ids:
            return  [('id','in',ids)]
        return  [('id','=','0')]
    
    def _search_semaforo_dy(self, operator, value):
        ids = []
        for item in self.search([]):
            if operator == 'ilike':
                operator = '='
            if operator == 'not ilike':
                operator = '!='
            if item.finalizado:
                semaforo_dy = 'N.A.'
            else:
                semaforo_dy = self.calc_semaforo_remainder_dy(item.remainder_dy, item.marge_dy)
            if value.lower() == 'na' or value.lower() == 'n.a' or value.lower() == 'n.a.':
                value = 'N.A.'
                if operator == '=' and semaforo_dy == value:
                    ids.append(item.id)
                if operator == '!=' and semaforo_dy != value:
                    ids.append(item.id)
            if value.lower() == semaforo_dy.lower() and operator == '=':
                ids.append(item.id)
            if value.lower() != semaforo_dy.lower() and operator == '!=':
                ids.append(item.id)

        if ids:
            return  [('id','in',ids)]
        return  [('id','=','0')]
    

    @api.depends('perfil_formacion')
    def _get_alumno_from_pf(self):
        for item in self:
            item.alumno = item.perfil_formacion.alumno.id
    

    def _search_alumno_from_pf(self, operator, value):
        ids = []
        for item in self.search([]):
            if operator == '=':
                if item.perfil_formacion.alumno.id == value:
                    ids.append(item.id)
            if operator == '!=':
                if item.perfil_formacion.alumno.id != value:
                    ids.append(item.id)
        if ids:
            return  [('id','in',ids)]
        return  [('id','=','0')]


    descripcion = fields.Char("Descriptor")
    notas = fields.Text('Notas')
    periodicidad_dy = fields.Integer('Periodicidad dy')
    marge_dy = fields.Integer('Margen dy')
    perfil_formacion = fields.Many2one('leulit.perfil_formacion', 'Perfil formación', ondelete="cascade")
    piloto = fields.Many2one(related='perfil_formacion.piloto',comodel_name='leulit.piloto',string='Piloto',store=True)
    alumno = fields.Many2one(compute=_get_alumno_from_pf,comodel_name="leulit.alumno",string="Alumno",search=_search_alumno_from_pf,store=True)
    inactivo = fields.Boolean(related='perfil_formacion.inactivo',string='Perfil inactivo', store=False)
    is_template = fields.Boolean(related='perfil_formacion.is_template',string='Es plantilla')
    pf_curso_tmpl = fields.Many2one('leulit.perfil_formacion_curso', 'Perfil formación curso')
    last_done_history = fields.One2many('leulit.perfil_formacion_curso_last_done', 'pf_curso', 'Historial last done')
    last_done = fields.One2many('leulit.perfil_formacion_curso_last_done', 'pf_curso', 'Last done', domain=[('is_last', '=', True)])
    last_done_date = fields.Date(related='last_done.done_date',string='Done date')
    next_done_date = fields.Date(compute=_get_next_done_date,string='Next done date',store=False)
    remainder_dy = fields.Integer(compute=_get_remainder_dy,string='Remain. (DY)',search=_search_remainder_dy,store=False )
    semaforo_dy = fields.Char(compute=_get_semaforo_dy,string='Semáforo', search=_search_semaforo_dy, store=False)
    finalizado = fields.Boolean('Finalizado',default=False)
    curso = fields.Many2one(comodel_name='leulit.curso', string='Curso',domain=[('estado','=','activo')])
    estado = fields.Selection(related="curso.estado", selection=[('activo','Activo'),('inactivo','Inactivo')], string="Estado curso")
    last_parte = fields.Char(compute=_last_parte,string='Last parte',store=False)
    last_parte_id = fields.Char(compute=_last_parte_id,string='Last parte id',store=False)


    def replicar_curso(self):
        perfil_formacion = self.env.context.get('perfil_formacion')
        perfil_formacion_tmpl = self.env.context.get('perfil_formacion_tmpl')
        _logger.error("Contexto perfil_formacion: %s", perfil_formacion)
        _logger.error("Contexto perfil_formacion_tmpl: %s", perfil_formacion_tmpl)
        for item in self:
            item.copy(default={'perfil_formacion':perfil_formacion[0][2][0], 'is_template':False, 'pf_curso_tmpl': item.id})
        
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_popup_replicar_cursos_pf_form')
        view_id = view_ref and view_ref[1] or False
        context = {
            'default_perfil_formacion_tmpl': perfil_formacion_tmpl,
            'default_perfil_formacion_replica_ids': perfil_formacion,
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
