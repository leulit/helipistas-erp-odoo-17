# -*- encoding: utf-8 -*-

from optparse import check_builtin
from tabnanny import check
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class leulit_parte_escuela(models.Model):
    _name           = "leulit.parte_escuela"
    _inherit        = ['mail.thread']
    _description    = "Parte Escuela"
    _table          = "leulit_parte_teorica"
    _order          = "fecha desc, id desc"


    def wkf_act_cerrado(self):
        check = True
        for item in self:
            if not item.name:
                check = False
                raise UserError('El campo "Contenido" está vacío')
            if not item.profesor:
                check = False
                raise UserError('No hay profesor asignado en el parte de escuela')
            if len(item.rel_curso_alumno) == 0:
                check = False
                raise UserError('No hay alumnos asignados en el parte de escuela')
            if item.profesor.id != self.env.user.partner_id.id:
                if item.isreadonly:
                    check = False
                    raise UserError('Usuario no autorizado a cerrar el parte de escuela. Tan sólo el profesor puede cerrar el parte de escuela')
        if check:
            for rec in self:
                if rec.vuelo_id and rec.vuelo_id.estado != 'cerrado':
                    raise UserError('No puede cerrarse directamente un parte de teóricas asociado a un parte de vuelo')
                else:
                    alumnos = []
                    for rel_curso_alu in rec.rel_curso_alumno:
                        if rel_curso_alu.alumno.id not in alumnos:
                            rec.actualizacion_parte_escuela_teoricos_practicos(rec.fecha, rec.hora_start, rec.tiempo, rel_curso_alu.alumno, False, False, rec.comentario, rec.valoracion)
                            alumnos.append(rel_curso_alu.alumno.id)
                    if not rec.valoracion and not rec.comentario:
                        raise UserError('Para cerrar un parte de escuela se necesita poner un comentario y una valoracion')


    def actualizacion_parte_escuela_teoricos_practicos(self, fecha, h_salida, tiempo_servicio, alumno, verificado, cierro_parte, comentario, valoracion):
        if cierro_parte == True:
            return True
        else:
            p_escuela = self.rel_curso_alumno
            if not self.vuelo_id:
                for parte in p_escuela:
                    if parte.sil_test == True:
                        if not parte.rel_docs:
                            raise UserError('Este Parte contiene un Silabus TEST que debe contener archivos adjuntos obligatorios.')
                        if parte.nota == -1:
                            raise UserError('Este Parte contiene un Silabus TEST que debe contener nota obligatoria.')
                    if parte.sil_valoracion == True:
                        if not parte.valoracion:
                            raise UserError('Este Parte contiene una valoración en el Silabus que debe tener un valor obligatorio.')

                self.hora_start = h_salida
                self.hora_end = h_salida + tiempo_servicio
                self.tiempo = tiempo_servicio
                self.fecha = fecha
                self.comentario = comentario
                self.valoracion = valoracion
            self.estado = 'cerrado'
            self.updateTiempos()
            # OBTENER CURSOS DEL PARTE DE VUELO
            cursos=[]
            for parte in p_escuela:
                if parte.alumno == alumno or parte.alumno.piloto_id == verificado:
                    curso = parte.rel_curso
                    if curso.id not in cursos:
                        cursos.append(curso.id)
            idalumno = 0
            if alumno:
                idalumno = alumno.id
            elif verificado:
                idalumno = self.env['leulit.alumno'].search([('piloto_id','=',verificado.id)]).id
            _logger.error('Cursos: %s', cursos)
            _logger.error('idalumno: %s', idalumno)
            # MODIFICAR PERFIL PILOTO
            self.env['leulit.silabus'].act_curs_done(idalumno, fecha, cursos, self.id)

            return True

    def wkf_act_cancelado(self):
        for item in self:
            item.estado = 'cancelado'


    def verficar_por_orden(self):
        for item in self:
            item.rel_curso_alumno.verficar_por_orden()


    def metodo_a_ejecutar(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20210430_1419_form')
        view_id = view_ref and view_ref[1] or False
        for item in self:
            context = {
                'parte_escuela_id'             : item.id,
                'default_parte_escuela_id'     : item.id,
            }
        return {
            'type'           : 'ir.actions.act_window',
            'name'           : 'Parte Escuela Cursos - Alumnos',
            'res_model'      : 'leulit.popup_rel_parte_escuela_cursos_alumnos',
            'view_type'      : 'form',
            'view_mode'      : 'form',
            'view_id'        : view_id,
            'target'         : 'new',
            'nodestroy'      : True,
            'context'         : context,
            }

    def run_updateTiempos(self):
        partes = self.search([('fecha','>=','2022-01-26')])
        for parte in partes:
            parte.updateTiempos()
    
    def updateTiempos(self):
        alumnos = []
        
        if self.rel_curso_alumno:
            for item in self.rel_curso_alumno:
                if item.alumno.id not in alumnos:
                    alumnos.append(item.alumno.id)
            for alumno in alumnos:
                sql = (
                    'SELECT count(id) as nitems FROM leulit_rel_parte_escuela_cursos_alumnos '
                    'WHERE rel_parte_escuela = {0} AND alumno = {1} '
                    'GROUP BY rel_silabus'
                ).format( self._origin.id, alumno)
                self._cr.execute(sql)
                items = list(self._cr.fetchall())
                nitems = len(items)
                tiempo = self.tiempo / nitems
                for item in self.rel_curso_alumno:
                    if alumno == item.alumno.id:
                        item.tiempo = tiempo

    def _get_valoracion_options(self):
        return (
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
            ('apto', 'Apto'),
            ('noapto', 'No apto')
        )


    @api.depends('estado')
    def _is_readonly(self):
        for item in self:
            item.isreadonly = False
            if item.estado == 'cerrado':
                if not self.env.user.has_group("leulit_escuela.REscuela_responsable"):
                    item.isreadonly = True

    
    def isvueloato(self, idvuelo):
        cursosato = self.env['leulit.curso']._curso_ato()
        return self.env['leulit.parte_escuela'].search([('cursos','in',cursosato),('vuelo_id','=',idvuelo)], count=True) > 0


    def _search_curso(self, operator, value):
        idsitems = []
        if operator in ['=','in']:
            cursos = self.env['leulit.curso'].search([('id',operator,value)])
            for item in cursos:
                if item.id not in idsitems:
                    idsitems.append(item.id)
        else:
            cursos = self.env['leulit.curso'].search([('name',operator,value)])
            for item in cursos:
                if item.id not in idsitems:
                    idsitems.append(item.id)
        rel_silabus_partes = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_curso','in',idsitems)])
        idsitems = []
        for item in rel_silabus_partes:
            if item.rel_parte_escuela.id not in idsitems:
                idsitems.append(item.rel_parte_escuela.id)        
        return [('id','in',idsitems)]   


    def _search_ato(self, operator, value):
        recs = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_curso.ato', operator, value)])
        return [('id','in',recs.mapped('rel_parte_escuela.id'))]


    def _search_silabus(self, operator, value):
        idssilabus = []
        if operator in ['=','in']:
            silabus = self.env['leulit.silabus'].search([('id',operator,value)])
            for itemsilabus in silabus:
                if itemsilabus.id not in idssilabus:
                    idssilabus.append(itemsilabus.id)
        else:
            silabus = self.env['leulit.silabus'].search([('name',operator,value)])
            for itemsilabus in silabus:
                if itemsilabus.id not in idssilabus:
                    idssilabus.append(itemsilabus.id)
        rel_silabus_partes = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_silabus','in',idssilabus)]) 
        idsquery = []
        for x in rel_silabus_partes:
            if x.rel_parte_escuela.id not in idsquery:
                idsquery.append(x.rel_parte_escuela.id)
        return [('id','in',idsquery)]            

    
    def _get_silabus(self):
        for item in self:
            items2 = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_parte_escuela','=',item.id)])
            idsquery = []
            for x in items2:
                if x.rel_silabus.id not in idsquery:
                    idsquery.append(x.rel_silabus.id)            
            item.silabus = idsquery


    def _get_uid_in_alumnos(self):
        for item in self:
            valor = False
            for item2 in item.rel_curso_alumno:
                if item2.alumno.userid.id == self.env.uid:
                    valor = True
            item.uid_in_alumnos = valor


    def _search_uid_in_alumnos(self, operator, value):    
        ids = []            
        for item in self.env['leulit.parte_escuela'].search([]):            
            for item2 in item.rel_curso_alumno:
                if item2.alumno.userid.id == self.env.uid:
                    ids.append( item.id )
        return [('id', 'in', ids)]

    

    def _get_alumnos(self):
        for item in self:
            items2 = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_parte_escuela','=',item.id)])
            idsitems = []
            for item21 in items2:
                if item21.alumno.id not in idsitems:
                    idsitems.append(item21.alumno.id)
            item.alumnos = idsitems        


    def _search_alumno(self, operator, value):
        idsitems = []
        if operator in ['=','in']:
            alumnos = self.env['leulit.alumno'].search([('id',operator,value)])
            for item in alumnos:
                if item.id not in idsitems:
                    idsitems.append(item.id)
        else:
            alumnos = self.env['leulit.alumno'].search([('name',operator,value)])
            for item in alumnos:
                if item.id not in idsitems:
                    idsitems.append(item.id)
        rel_silabus_partes = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('alumno','in',idsitems)])
        idsitems = []
        for item in rel_silabus_partes:
            if item.rel_parte_escuela.id not in idsitems:
                idsitems.append(item.rel_parte_escuela.id)
        return [('id','in',idsitems)]

    #@api.depends('rel_curso_alumno')
    def _get_asignatura(self):
        res = {}
        for item in self:
            vals = [] 
            if item.rel_curso_alumno:
                for item2 in item.rel_curso_alumno:
                    if item2.rel_silabus:
                        if item2.rel_silabus.asignatura_id:
                            vals.append(item2.rel_silabus.asignatura_id.id) 
            item.asignatura = vals                  
        return res

    @api.depends('vuelo_id')
    def _get_tipo(self):
        res = {}
        for item in self:
            if item.vuelo_id:
                item.tipo = 'practico'
            else:
                item.tipo = 'teorico'
        return res

    @api.model
    def _get_cursos(self):
        for item in self:
            items2 = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_parte_escuela','=',item.id)])
            idsquery = []
            [idsquery.append(x.rel_curso.id) for x in items2 if x not in idsquery]
            item.cursos = idsquery

    @api.model
    def _get_ato(self):
        for item in self:
            items2 = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_parte_escuela','=',item.id)])
            for linea in items2:
                if linea.rel_curso.ato:
                    item.ato = True


    @api.depends('rel_curso_alumno','estado')
    def _is_verificado(self):
        for item in self:
            valor = ''
            verificado = True
            for item2 in item.rel_curso_alumno:
                if not item2.verificado:
                    verificado = False
                    break
            if item.estado == 'cerrado' and verificado:
                valor = 'cerrado_y_validado'
            elif item.estado == 'cerrado' and not verificado:
                valor = 'cerrado_no_validado'
            item.silverificado = valor


    @api.onchange('hora_end','hora_start')
    def onchange_updatetiempos(self):
        if self.hora_end and self.hora_start:
            self.tiempo = self.hora_end - self.hora_start
            self.updateTiempos()


    @api.depends('rel_curso_alumno','estado')
    def _is_verificado_por_alumno(self):
        for item in self:
            valor = False
            verificado = True
            for item2 in item.rel_curso_alumno:
                if item2.alumno.userid.id == self.env.uid:
                    if not item2.verificado:
                        verificado = False
                        break
            if item.estado == 'cerrado' and verificado:
                valor = True
            item.silverificado_por_alumno = valor
            

    @api.depends('silverificado')
    def _validado(self):        
        for item in self:
            verificado = ""
            item.validado = verificado and verificado == 'cerrado_y_validado'


    @api.depends('rel_curso_alumno')
    def _get_domainSilabus(self):
        ids_rel = []
        for item in self:
            ids_rel = []
            for item2 in item.rel_curso_alumno:
                if item2.alumno.userid.id == self.env.uid:
                    ids_rel.append(item2.id)
            item.domainSilabus = ids_rel


    def _search_domainSilabus(self, operator, value):
        res = []
        #for item in self.search([]):
        #    if condition(args[0][1], item['domainSilabus'], args[0][2]):
        #        res.append(item['id'])
        return [('id', 'in', res)]

    def _get_uid_responsable(self):
        for item in self:
            item.uid_responsable = False
            if self.env.user.has_group("leulit_escuela.REscuela_responsable"):
                item.uid_responsable = True

    def _search_uid_responsable(self, operator, value):
        items = []
        if self.env.user.has_group("leulit_escuela.REscuela_responsable"):
            items = self.search([])
        return [('id', 'in', items.ids)]     


    def wizard_change_data(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20221122_1708_tree')
        view_id = view_ref and view_ref[1] or False
        items = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_parte_escuela','=',self.id)])
        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Lineas de silabus',
           'res_model'      : 'leulit.rel_parte_escuela_cursos_alumnos', 
           'view_id'        : view_id,
           'view_type'      : 'form',
           'view_mode'      : 'tree',
           'domain'         : [('id', 'in', items.ids)],
        }


    def verificar_alumno_all(self):
        for item in self:
            for silabus in item.domainSilabus:
                silabus.verificar_alumno()


    name = fields.Char('Contenido')
    comentario = fields.Text('Comentario')
    vuelo_id = fields.Many2one(comodel_name='leulit.vuelo', string='Vuelo', ondelete='set null')
    profesor = fields.Many2one(comodel_name='leulit.profesor',string='Profesor',ondelete='restrict')
    profesor_foto = fields.Binary(related='profesor.image_1920',string='Foto empleado',store=False)
    profesoradjunto = fields.Many2one(comodel_name='leulit.profesor',string='Profesor adjunto',ondelete='restrict')
    profesor_adjunto_foto = fields.Binary(related='profesoradjunto.image_1920',string='Foto empleado',store=False)
    fecha = fields.Date('Fecha', required=True)
    hora_start = fields.Float('Hora inicio', required=True)
    rip_tiempo = fields.Float('rip tiempo')
    hora_end = fields.Float('Hora Fin', required=True)
    tiempo = fields.Float("Tiempo")
    valoracion = fields.Selection(_get_valoracion_options,'Valoración')
    estado = fields.Selection([('pendiente','Pendiente'),('cerrado','Cerrado'),('cancelado','Cancelado')], 'Estado',default="pendiente", required=True)
    write_uid = fields.Many2one(comodel_name='res.users', string='by User', readonly=True)
    create_uid = fields.Many2one(comodel_name='res.users', string='created by User', readonly=True)
    rel_curso_alumno = fields.One2many('leulit.rel_parte_escuela_cursos_alumnos','rel_parte_escuela', 'Relación')
    cursos = fields.One2many(compute=_get_cursos,comodel_name='leulit.curso',string='Cursos',search=_search_curso)
    ato = fields.Boolean(compute=_get_ato, string='ATO', search=_search_ato)
    alumnos = fields.One2many(compute=_get_alumnos,comodel_name='leulit.alumno',string='Alumnos',search=_search_alumno)
    silabus = fields.One2many(compute=_get_silabus,comodel_name='leulit.silabus',string='Silabus',search=_search_silabus)
    tipo = fields.Selection(compute=_get_tipo, string='Tipo', selection=[('teorico','Teórico'),('practico','Práctico')], store=False)
    isreadonly = fields.Boolean(compute='_is_readonly',string='Solo lectura',store=False)
    asignatura = fields.One2many(comodel_name='leulit.asignatura',compute=_get_asignatura,string='Asignatura',store=False)
    domainSilabus = fields.One2many(comodel_name='leulit.rel_parte_escuela_cursos_alumnos',compute=_get_domainSilabus,string='Cursos',search=_search_domainSilabus)
    silverificado = fields.Char(compute=_is_verificado,string='Silabus Verificado',store=False)
    silverificado_por_alumno = fields.Boolean(compute=_is_verificado_por_alumno,string='Silabus Verificados por Alumno')
    validado = fields.Boolean(compute=_validado,string='Cerrado y validado',store=False)
    event = fields.Many2one(comodel_name='calendar.event', string='Evento')
    presencial = fields.Boolean('Presencial',default=True)
    fase_vuelo = fields.Selection([('fase_1', 'Fase 1'), ('fase_2', 'Fase 2')], 'Fase de vuelo')
    presupuestos = fields.Many2many('sale.order', 'parte_teorica_so_rel','pt_id','so_id', string="Presupuestos")
    uid_in_alumnos = fields.Boolean(compute=_get_uid_in_alumnos,string='Usuarios',store=False,search=_search_uid_in_alumnos)
    active = fields.Boolean(string='Activo',default=True)
    uid_responsable = fields.Boolean(compute=_get_uid_responsable,string='Soy responsable?',store=False,search=_search_uid_responsable)
    

    @api.constrains('rel_curso_alumno','profesor','profesoradjunto','hora_start','hora_end','fecha')
    def check_unique_alumno_profesor_in_date_and_hours(self):
        for record in self:
            for item in self.env['leulit.vuelo'].search([('id','!=',record.vuelo_id.id),('alumno','=',False),('verificado','=',False),('estado','=','cerrado'),('fechavuelo','=',record.fecha)]):
                notmine = False
                if record.vuelo_id:
                    if record.vuelo_id.id != item.id:
                        notmine = True
                else:
                    notmine = True
                if notmine == True:
                    if item.piloto_id or item.operador or item.piloto_supervisor_id:
                        check_isequals = False
                        check_isexist = False
                        if item.horasalida == record.hora_start and item.horallegada == record.hora_end:
                            check_isequals = True
                        if item.horasalida >= record.hora_start and item.horallegada >= record.hora_end and item.horasalida < record.hora_end:
                            check_isequals = True
                        if item.horasalida <= record.hora_start and item.horallegada <= record.hora_end and item.horallegada > record.hora_start:
                            check_isequals = True
                        if item.horasalida >= record.hora_start and item.horallegada <= record.hora_end:
                            check_isequals = True
                        if item.horasalida <= record.hora_start and item.horallegada >= record.hora_end:
                            check_isequals = True
                        name = ''
                        tipo = ''
                        if check_isequals:
                            if item.piloto_id and record.profesoradjunto:
                                if record.profesoradjunto.partner_id.id == item.piloto_id.partner_id.id:
                                    name = item.piloto_id.name
                                    tipo = 'piloto'
                                    check_isexist = True
                            if item.operador and record.profesoradjunto:
                                if record.profesoradjunto.partner_id.id == item.operador.partner_id.id:
                                    name = item.operador.name
                                    tipo = 'operador'
                                    check_isexist = True
                            if item.piloto_supervisor_id and record.profesoradjunto:
                                if record.profesoradjunto.partner_id.id == item.piloto_supervisor_id.partner_id.id:
                                    name = item.piloto_supervisor_id.name
                                    tipo = 'piloto supervisor'
                                    check_isexist = True
                            if item.piloto_id and record.profesor:
                                if record.profesor.partner_id.id == item.piloto_id.partner_id.id:
                                    name = item.piloto_id.name
                                    tipo = 'piloto'
                                    check_isexist = True
                            if item.operador and record.profesor:
                                if record.profesor.partner_id.id == item.operador.partner_id.id:
                                    name = item.operador.name
                                    tipo = 'operador'
                                    check_isexist = True
                            if item.piloto_supervisor_id and record.profesor:
                                if record.profesor.partner_id.id == item.piloto_supervisor_id.partner_id.id:
                                    name = item.piloto_supervisor_id.name
                                    tipo = 'piloto supervisor'
                                    check_isexist = True
                            if record.rel_curso_alumno:
                                for record_curso_al in record.rel_curso_alumno:
                                    if record_curso_al.alumno:
                                        if item.piloto_id:
                                            if record_curso_al.alumno.partner_id.id == item.piloto_id.partner_id.id:
                                                name = item.piloto_id.name
                                                tipo = 'piloto'
                                                check_isexist = True
                                        if item.operador:
                                            if record_curso_al.alumno.partner_id.id == item.operador.partner_id.id:
                                                name = item.operador.name
                                                tipo = 'operador'
                                                check_isexist = True
                                        if item.piloto_supervisor_id:
                                            if record_curso_al.alumno.partner_id.id == item.piloto_supervisor_id.partner_id.id:
                                                name = item.piloto_supervisor_id.name
                                                tipo = 'piloto supervisor'
                                                check_isexist = True
                        if check_isexist:
                            raise ValidationError("El recurso %s es usado como %s en el parte de vuelo [%s]%s con hora de inicio: %s y con hora de fin: %s" % (name, tipo, item.id, item.codigo, utilitylib.leulit_float_time_to_str(item.horasalida), utilitylib.leulit_float_time_to_str(item.horallegada)))
            
            for item in self.env['leulit.parte_escuela'].search([('id','!=',record.id),('fecha','=',record.fecha),('estado','=','cerrado')]):
                if item.rel_curso_alumno or item.profesor:
                    check_isequals = False
                    check_isexist = False
                    if item.hora_start == record.hora_start and item.hora_end == record.hora_end:
                        check_isequals = True
                    if item.hora_start >= record.hora_start and item.hora_end >= record.hora_end and item.hora_start < record.hora_end:
                        check_isequals = True
                    if item.hora_start <= record.hora_start and item.hora_end <= record.hora_end and item.hora_end > record.hora_start:
                        check_isequals = True
                    if item.hora_start >= record.hora_start and item.hora_end <= record.hora_end:
                        check_isequals = True
                    if item.hora_start <= record.hora_start and item.hora_end >= record.hora_end:
                        check_isequals = True
                    name = ''
                    tipo = ''
                    if check_isequals:
                        if record.profesoradjunto and item.profesor:
                            if item.profesor.id == record.profesoradjunto.id:
                                name = item.profesor.name
                                tipo = 'profesor'
                                check_isexist = True
                        if record.profesoradjunto and item.profesoradjunto:
                            if item.profesoradjunto.id == record.profesoradjunto.id:
                                name = item.profesor.name
                                tipo = 'profesor adjunto'
                                check_isexist = True
                        if record.profesor and item.profesoradjunto:
                            if item.profesoradjunto.id == record.profesor.id:
                                name = item.profesor.name
                                tipo = 'profesor adjunto'
                                check_isexist = True
                        if record.profesor and item.profesor:
                            if item.profesor.id == record.profesor.id:
                                name = item.profesor.name
                                tipo = 'profesor'
                                check_isexist = True
                        if item.rel_curso_alumno:
                            for curso_al in item.rel_curso_alumno:
                                if curso_al.alumno:
                                    if record.profesoradjunto:
                                        if curso_al.alumno.partner_id.id == record.profesoradjunto.partner_id.id:
                                            name = curso_al.alumno.name
                                            tipo = 'alumno'
                                            check_isexist = True
                                    if record.profesor:
                                        if curso_al.alumno.partner_id.id == record.profesor.partner_id.id:
                                            name = curso_al.alumno.name
                                            tipo = 'alumno'
                                            check_isexist = True
                                    if record.rel_curso_alumno:
                                        for record_curso_al in record.rel_curso_alumno:
                                            if record_curso_al.alumno:
                                                if curso_al.alumno.id == record_curso_al.alumno.id:
                                                    name = curso_al.alumno.name
                                                    tipo = 'alumno'
                                                    check_isexist = True
                    if check_isexist:
                        raise ValidationError("El recurso %s es usado como %s en el parte de escuela [%s]%s con hora de inicio: %s y con hora de fin: %s" % (name, tipo, item.id, item.name, utilitylib.leulit_float_time_to_str(item.hora_start), utilitylib.leulit_float_time_to_str(item.hora_end)))



    def get_partes_error(self):
        _logger.error("get_partes_error ")
        threaded_calculation = threading.Thread(target=self.run_get_partes_error, args=([]))
        _logger.error("get_partes_error start thread")
        threaded_calculation.start()
        return {}


    def run_get_partes_error(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            for parte in self.search([('vuelo_id','!=',False),('estado','=','cerrado'),('fecha','>=','2023-01-01')]):
                if parte.vuelo_id.alumno:
                    alumno_vuelo = parte.vuelo_id.alumno
                if parte.vuelo_id.verificado:
                    alumno_vuelo = parte.vuelo_id.verificado.alumno
                for item in parte.rel_curso_alumno:
                    if item.alumno != alumno_vuelo:
                        _logger.error('####### parte de teoricas: %s, Alumno: %s, Alumno Vuelo: %s' % (parte.id, item.alumno.name, alumno_vuelo.name))
                        break

            _logger.error("get_partes_error fin")