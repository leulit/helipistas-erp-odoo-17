# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class leulit_alumno(models.Model):
    _name           = "leulit.alumno"
    _description    = "leulit_alumno"
    _inherits       = {'res.partner': 'partner_id'}
    _rec_name       = "name"
    _inherit        = ['mail.thread']


    def _get_horas_by_tipo_curso_asignatura(self, idalumno, idcurso, idasignatura, tipo):
        sql = "SELECT COALESCE(SUM(tiempo),0) AS suma FROM "
        sql = sql + "(select rel_curso, alumno, idasignatura,tiempo, tipo FROM "
        sql = sql + "(SELECT leulit_rel_parte_escuela_cursos_alumnos.*,  coalesce(leulit_asignatura.id,0) AS idasignatura,leulit_silabus.tipo "
        sql = sql + "FROM leulit_rel_parte_escuela_cursos_alumnos "
        sql = sql + "INNER JOIN leulit_silabus ON leulit_rel_parte_escuela_cursos_alumnos.rel_silabus = leulit_silabus.id "
        sql = sql + "LEFT OUTER JOIN leulit_asignatura ON leulit_silabus.asignatura_id = leulit_asignatura.id ) as tabla "
        sql = sql + "WHERE alumno = %s AND rel_curso = %s AND idasignatura = %s AND tipo = '%s') AS tabla2"
        sql = sql % (idalumno, idcurso, idasignatura, tipo)
        self._cr.execute(sql)
        return list(self._cr.fetchall()[0])[0]

    def informe_cursos_alu_practicas(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20211012_1347_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_alumno': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Informe prácticas',
            'res_model': 'leulit.wizard_report_practicas_curso',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    def informe_cursos_alu_teoricas(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20211013_1155_form')
        view_id = view_ref and view_ref[1] or False
        
        context = {
            'default_alumno': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Informe teóricas',
            'res_model': 'leulit.wizard_report_teoricas_curso',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    def informe_general_cursos_alu(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_alumno_wizard_report_practicas')
        view_id = view_ref and view_ref[1] or False
        
        context = {
            'default_alumno': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Informe General',
            'res_model': 'leulit.wizard_report_curso',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    def open_popup_tabla_progresos(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20221028_1210_form')
        view_id = view_ref and view_ref[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tabla de Progreso',
            'res_model': 'leulit.alumno',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': self.id,
            'target': 'new',
        }


    @api.depends()
    def _get_partes_escuela(self):
        for item in self:
            item.parte_escuela_ids = self.env['leulit.parte_escuela'].search([('rel_curso_alumno.alumno.id', 'in', [item.id])])


    @api.depends()
    def _get_partesescuela_teoria(self):
        for item in self:
            item.partesescuela_teorico_ids = self.env['leulit.parte_escuela'].search([('rel_curso_alumno.alumno.id', 'in', [item.id]), ('tipo', '=', 'teorico')])


    @api.depends()
    def _get_partesescuela_practica(self):
        for item in self:
            item.partesescuela_practico_ids = self.env['leulit.parte_escuela'].search([('rel_curso_alumno.alumno.id', 'in', [item.id]), ('tipo', '=', 'practico')])


    @api.depends('partesescuela_teorico_ids')
    def _get_total_horas_teorica(self):
        for item in self:
            if item.partesescuela_teorico_ids:
                sql = "SELECT COALESCE(SUM(tiempo),0) as suma FROM leulit_parte_teorica WHERE id in (%s)" % ','.join(str(i.id) for i in item.partesescuela_teorico_ids)
                self._cr.execute(sql)
                item.total_horas_teorica = list(self._cr.fetchall()[0])[0]
            else:
                item.total_horas_teorica = 0


    @api.depends('partesescuela_practico_ids')
    def _get_total_horas_practica(self):
        for item in self:
            if item.partesescuela_practico_ids:
                sql = "SELECT COALESCE(SUM(tiempo),0) as suma FROM leulit_parte_teorica WHERE id in (%s)" % ','.join(str(i.id) for i in item.partesescuela_practico_ids)
                self._cr.execute(sql)
                item.total_horas_practica = list(self._cr.fetchall()[0])[0]
            else:
                item.total_horas_practica = 0


    @api.depends('parte_escuela_ids')
    def _get_total_horas(self):
        for item in self:
            if item.parte_escuela_ids:
                sql = "SELECT COALESCE(SUM(tiempo),0) as suma FROM leulit_parte_teorica WHERE id in (%s)" % ','.join(str(i.id) for i in item.parte_escuela_ids)
                self._cr.execute(sql)
                item.total_horas = list(self._cr.fetchall()[0])[0]
            else:
                item.total_horas = 0


    @api.depends('rel_horas_fact')
    def _get_total_horas_practica_fact(self):
        for item in self:
            if item.rel_horas_fact:
                sql = "SELECT COALESCE(SUM(horas_practica_fact),0) as suma FROM leulit_alumno_horas_facturadas WHERE id in (%s)" % ','.join(str(i) for i in item.rel_horas_fact)
                self._cr.execute(sql)
                item.total_horas_practica_fact = list(self._cr.fetchall()[0])[0]
            else:
                item.total_horas_practica_fact = 0


    @api.depends('rel_horas_fact')
    def _get_total_horas_fact(self):
        for item in self:
            if item.rel_horas_fact:
                sql = "SELECT COALESCE(SUM(horas_teorica_fact)+SUM(horas_teorica_fact),0) as suma FROM leulit_alumno_horas_facturadas WHERE id in (%s)" % ','.join(str(i) for i in item.rel_horas_fact)
                self._cr.execute(sql)
                item.total_horas_fact = list(self._cr.fetchall()[0])[0]
            else:
                item.total_horas_fact = 0


    def _get_attachments(self):
        for item in self:
            item.attachement_ids = self.env['ir.attachment'].search([('res_model', '=', 'leulit.alumno'),('res_id', '=', item.id)])


    def metodo_historial_a_ejecutar(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20201130_1125_informes_historial_popup_form')
        view_id = view_ref and view_ref[1] or False

        context = {
            'default_alumno_id': self.id
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Historial',
            'res_model': 'leulit.informes_historial_popup',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }


    def xmlrpc_cursos(self):
        cursos = []
        for item in self:
            for curso in self.env['leulit.rel_alumno_curso'].browse(item.rel_alumno_curso_ids.ids):
                cursos.append( {'id' : curso.curso_id.id, 'name': curso.curso_id.name} )
        return cursos

    
    def xmlrpc_asignaturas(self, idcurso, tipo):
        teoricas  = {}
        sesiones  = {}
        for item in self:
            if idcurso:
                idcurso = int(idcurso)
                silabus = self.env['leulit.silabus'].search([('curso_id', '=', idcurso), ('tipo', '=', tipo)],order="orden ASC")
                total_duracion = 0
                strduracion = '0:00'
                totalreal = 0
                strreal = '0:00'
                name = 'Total'
                id_asignatura = ''
                for itemsilabus in silabus:
                    total_duracion += itemsilabus.duracion
                    if itemsilabus.asignatura_id:
                        if not itemsilabus.asignatura_id.id in teoricas:
                            teoricas.update({itemsilabus.asignatura_id.id: {'duracion': itemsilabus.duracion,
                                                                            'id': itemsilabus.asignatura_id.id,
                                                                            'name': itemsilabus.asignatura_id.descripcion}})
                        else:
                            asignatura = teoricas[itemsilabus.asignatura_id.id]
                            duracion = asignatura['duracion'] + itemsilabus.duracion
                            asignatura.update({'duracion': duracion, 'strduracion' : utilitylib.decimal_time_to_str_without_seconds(duracion) })
                            teoricas.update({itemsilabus.asignatura_id.id: asignatura})
                for asignatura in teoricas:
                    horas = self.xmlrpc_asignaturas_horas(item.id, asignatura, idcurso, tipo)
                    totalreal += horas
                    teoricas[asignatura].update({'total_real' : horas, 'str_total_real': utilitylib.decimal_time_to_str_without_seconds(horas)})
                
                strreal = utilitylib.decimal_time_to_str_without_seconds(totalreal)
                strduracion = utilitylib.decimal_time_to_str_without_seconds(total_duracion)
                teoricas.update({'Total':  {'duracion': total_duracion,
                                            'total_real': totalreal,
                                            'id': id_asignatura,
                                            'name': name,
                                            'str_total_real': strreal,
                                            'strduracion': strduracion}})


                tipo = 'practica'
                sesiones = self.get_sesiones(idcurso)
                for sesion in sesiones:
                    result = self.xmlrpc_sesion_horas(item.id, sesion, idcurso, tipo)
                    sesiones[sesion].update({
                        'total_doblemando': result['total_doblemando'],
                        'total_pic': result['total_pic'],
                        'total_spic': result['total_spic'],
                        'total_otros': result['total_otros'],
                    })

        return {
            'teoricas' : teoricas,
            'practicas' : sesiones,
        }


    def xmlrpc_asignaturas_horas(self, idalumno, idasignatura, idcurso, tipo):
        sql = '''
            SELECT
            coalesce(sum("leulit_rel_parte_escuela_cursos_alumnos".tiempo),0) as cantidad
            FROM
            "leulit_rel_parte_escuela_cursos_alumnos"
            JOIN "leulit_silabus"
            ON "leulit_rel_parte_escuela_cursos_alumnos"."rel_silabus" = "leulit_silabus"."id" 
            JOIN "leulit_alumno"
            ON "leulit_rel_parte_escuela_cursos_alumnos"."alumno" = "leulit_alumno"."id"
            JOIN "leulit_piloto"
            ON "leulit_alumno"."piloto_id" = "leulit_piloto"."id" 
            WHERE
            "leulit_alumno"."id" = {0}
            and
            "leulit_silabus"."asignatura_id" = {1}       
            and
            "leulit_rel_parte_escuela_cursos_alumnos"."rel_curso" = {2}
            and
            "leulit_silabus"."tipo" = '{3}'
            and
            "leulit_rel_parte_escuela_cursos_alumnos".verificado = 't'
        '''.format(idalumno,idasignatura,idcurso,tipo)
        item = utilitylib.runQueryReturnOne(self._cr, sql)
        return item['cantidad']


    def get_sesiones(self, idcurso):
        sql = '''
                    SELECT
                        orden, duracion, sesion
                    FROM
                        leulit_silabus
                    WHERE
                        curso_id = {0}
                    AND
                        tipo = 'practica'       
                    AND
                        sesion != 'nodef'
                    AND 
                        sesion IS NOT NULL
                '''.format(idcurso)
        items = utilitylib.runQuery(self._cr, sql)
        sesiones = {}
        for item in items:
            if item['sesion']:
                if not item['sesion'] in sesiones:
                    sesiones.update({item['sesion'] : {'duracion': item['duracion'], 'name': item['sesion'],'total_doblemando':0.0,'total_pic':0.0,'total_spic':0.0,'total_otros':0.0}})
                else:
                    sesion = sesiones[item['sesion']]
                    duracion = sesion['duracion'] + item['duracion']
                    sesion.update({'duracion': duracion})
                    sesiones.update({item['sesion']: sesion})
        return sesiones


    def datos_sesiones(self, alumnoid, sesion,idcurso,tipo):
        sql = '''
                    SELECT
                        "leulit_rel_parte_escuela_cursos_alumnos".tiempo,
                        "leulit_rel_parte_escuela_cursos_alumnos".rel_parte_escuela,
                        "leulit_vuelo".piloto_id,
                        "leulit_vuelo".doblemando,
                        "leulit_silabus"."name",
                        "leulit_rel_parte_escuela_cursos_alumnos".rel_alumnos,
                        "leulit_rel_parte_escuela_cursos_alumnos".alumno,
                        "leulit_parte_teorica".name as parte_teorica
                    FROM
                        "leulit_rel_parte_escuela_cursos_alumnos"
                        JOIN "leulit_silabus"
                        ON "leulit_rel_parte_escuela_cursos_alumnos"."rel_silabus" = "leulit_silabus"."id" 
                        JOIN "leulit_alumno"
                        ON "leulit_rel_parte_escuela_cursos_alumnos"."alumno" = "leulit_alumno"."id" 
                        JOIN "leulit_piloto"
                        ON "leulit_alumno"."piloto_id" = "leulit_piloto"."id" 
                        JOIN "leulit_parte_teorica"
                        ON "leulit_rel_parte_escuela_cursos_alumnos"."rel_parte_escuela" = "leulit_parte_teorica"."id" 
                        JOIN "leulit_vuelo"
                        ON "leulit_parte_teorica"."vuelo_id" = "leulit_vuelo"."id"
                    WHERE
                        "leulit_alumno"."id" = {0}
                        and
                        "leulit_silabus"."sesion" = '{1}'       
                        and
                        "leulit_rel_parte_escuela_cursos_alumnos"."rel_curso" = {2}
                        and
                        "leulit_silabus"."tipo" = '{3}'
                        and
                        "leulit_parte_teorica".estado = 'cerrado'
                '''.format(alumnoid, sesion, idcurso, tipo)
        items = utilitylib.runQuery(self._cr, sql)
        return items


    def xmlrpc_sesion_horas(self, alumnoid, sesion, idcurso,tipo, context={}):
        result = {
            'total_doblemando': 0.0,
            'total_pic': 0.0,
            'total_spic': 0.0,
            'total_otros': 0.0
        }
        items = self.datos_sesiones(alumnoid, sesion, idcurso, tipo)
        for item in items:
            piloto_alumno = self.env['leulit.alumno'].search([('piloto_id','=',item['rel_alumnos'])])
            if item['name'] and item['name'].upper().find('SPIC') > 0:
                result['total_spic'] += item['tiempo']
            else:
                if item['rel_alumnos']:
                    alumno_piloto_id = item['rel_alumnos']
                else:
                    alumno = self.env['leulit.alumno'].search([('id','=',item['alumno'])])
                    alumno_piloto_id = alumno.piloto_id.id
                if item['piloto_id'] == alumno_piloto_id:
                    result['total_pic'] += item['tiempo']
                else:
                    if item['doblemando']:
                        result['total_doblemando'] += item['tiempo']
                    else:
                        result['total_otros'] += item['tiempo']
        return result

    @api.depends('rel_alumno_curso_ids')
    def alumno_activo(self):
        for item in self:
            item.activo = False
            if item.rel_alumno_curso_ids:
                for curso in item.rel_alumno_curso_ids:
                    if curso.fecha_finalizacion == False:
                        item.activo = True
                        

    def _search_alumno_activo(self, operator, value):
        idsitems = []
        if operator in ['=','in']:
            for item in self.search([]):
                if item.rel_alumno_curso_ids:
                    for curso in item.rel_alumno_curso_ids:
                        if value == True:
                            if curso.fecha_finalizacion == False:
                                idsitems.append(item.id)
                        else:
                            if curso.fecha_finalizacion == True:
                                idsitems.append(item.id)
        return [('id','in',idsitems)]

    @api.model
    def getPartnerId(self):
        return self.partner_id.id
    
    @api.depends()
    def _piloto(self):
        for item in self:
            piloto = self.env['leulit.piloto'].search([('partner_id', '=', item.getPartnerId())])
            item.piloto = piloto

    @api.depends()
    def _userId(self):
        for item in self:
            item.userid = item.partner_id.user_ids

    def write(self,values):
        if 'active' in values and values['active'] == False:
        # Verificamos en todos los registros si hay alguno que no puede ser archivado
            alumnos_no_archivables = self.filtered(lambda alumno: alumno.activo)

            if alumnos_no_archivables:
                raise UserError(_("No puedes archivar un alumno con curso/s sin finalizar."))

        return super(leulit_alumno, self).write(values)

    
    def wizard_change_data(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20221122_1708_tree')
        view_id = view_ref and view_ref[1] or False
        items = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('alumno','=',self.id)])
        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Lineas de silabus',
           'res_model'      : 'leulit.rel_parte_escuela_cursos_alumnos', 
           'view_id'        : view_id,
           'view_type'      : 'form',
           'view_mode'      : 'tree',
           'domain'         : [('id', 'in', items.ids)],
        }
        

    @api.depends('userid')
    def _get_employee(self):
        for item in self:
            item.employee_id = False
            if item.userid:
                item.employee_id = self.env['hr.employee'].search([('user_id', '=', item.userid.id)])


    @api.depends('piloto_id','userid','is_alta')
    def _get_alta_alumno(self):
        for item in self:
            item.alta_all = False
            if item.piloto_id and item.userid:
                item.alta_all = True
            if item.is_alta:
                item.alta_all = True


    rel_alumno_curso_ids = fields.One2many('leulit.rel_alumno_curso', 'alumno_id', 'Cursos', required=True, domain=[('cursos_perfil_formacion','=',False)])
    piloto_id = fields.Many2one('leulit.piloto', 'Piloto', index=True)
    parte_escuela_ids = fields.One2many(compute='_get_partes_escuela',string='Partes de escuela',comodel_name='leulit.parte_escuela')
    rel_alumno_documentacion_ids= fields.One2many('leulit.rel_alumno_documentacion', 'alumno_id','Documentación', required=True)
    rel_alumno_evaluacion_ids = fields.One2many('leulit.rel_alumno_evaluacion', 'alumno_id', 'Evaluación',required=True)
    partesescuela_teorico_ids = fields.One2many(compute='_get_partesescuela_teoria',string='Partes escuela teórico',comodel_name='leulit.parte_escuela')
    partesescuela_practico_ids = fields.One2many(compute='_get_partesescuela_practica',string='Partes escuela práctico',comodel_name='leulit.parte_escuela')
    observaciones = fields.Text('Observaciones')
    total_horas_teorica = fields.Float(compute='_get_total_horas_teorica',string='Total horas teórica')
    total_horas_practica = fields.Float(compute='_get_total_horas_practica',string='Total horas práctica')
    total_horas = fields.Float(compute='_get_total_horas',string='Total horas')
    attachement_ids = fields.One2many(compute='_get_attachments',string='Ficheros',store=False,comodel_name='ir.attachment')
    activo = fields.Boolean(compute='alumno_activo',string='Activo',store=False,search=_search_alumno_activo)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Contacto', required=True, ondelete='cascade')
    fecha_nacimiento = fields.Date("Fecha de nacimiento", required=False)
    piloto = fields.One2many(compute=_piloto, string='Piloto', comodel_name='leulit.piloto')
    userid = fields.One2many(compute=_userId, string='Usuario', comodel_name='res.users')
    active = fields.Boolean(string='Activo',default=True)
    rel_parte_escuela_examenes = fields.One2many(comodel_name="leulit.rel_parte_escuela_cursos_alumnos", inverse_name="alumno", string="Examenes", domain=[('sil_test','=',True)])
    alta_all = fields.Boolean(compute=_get_alta_alumno, string="¿Alta alumno?")
    is_alta = fields.Boolean(string="Se ha dado de alta")
    employee_id = fields.Many2one(compute=_get_employee, comodel_name='hr.employee', string='Empleado', store=True)
    emergency_contact_empl = fields.Char(related='employee_id.emergency_contact', string='Contacto de Emergencia')
    emergency_phone_empl = fields.Char(related='employee_id.emergency_phone', string='Teléfono de emergencia')
    emergency_contact = fields.Char(string='Contacto de Emergencia')
    emergency_phone = fields.Char(string='Teléfono de emergencia')


    def remove_alta(self):
        self.userid.unlink()
        self.piloto_id.unlink()
        self.is_alta = False
        return True


    def alta_alumno(self):
        self.ensure_one()
        flag = True
        if not self.email:
            raise UserError("Falta un correo electrónico para poder dar de alta al alumno.")
        # USUARIO
        if not self.userid:
            category_base = self.env['ir.module.category'].search([('name','=','Rol Base')])
            category_operaciones = self.env['ir.module.category'].search([('name','=','Rol Operaciones')])
            category_actividad = self.env['ir.module.category'].search([('name','=','LEULIT - Gestión actividad')])
            category_escuela = self.env['ir.module.category'].search([('name','=','Rol Escuela')])
            category_planificacion = self.env['ir.module.category'].search([('name','=','Rol Planificación')])
            category_usuario = self.env['ir.module.category'].search([('name','=','Tipos de usuario')])
            group_base = self.env['res.groups'].search([('category_id','=',category_base.id),('name','=','Base')])
            group_escuela = self.env['res.groups'].search([('category_id','=',category_escuela.id),('name','=','Alumno')])
            group_operaciones = self.env['res.groups'].search([('category_id','=',category_operaciones.id),('name','=','Alumno')])
            group_actividad = self.env['res.groups'].search([('category_id','=',category_actividad.id),('name','=','User Actividad')])
            group_planificacion = self.env['res.groups'].search([('category_id','=',category_planificacion.id),('name','=','Planificación: Mi planificación')])
            group_usuario = self.env['res.groups'].search([('category_id','=',category_usuario.id),('name','=','Usuario interno')])
            user = self.env['res.users'].create({
                'login' : self.email,
                'name' : self.name,
                'partner_id' : self.partner_id.id,
                'lang': 'es_ES',
                'company_id': 1,
                'sel_groups_1_9_10': 10,
                'property_stock_customer' : None,
                'property_stock_supplier' : None,
            })
            grupos = [group_usuario.id,group_base.id,group_escuela.id,group_operaciones.id,group_actividad.id,group_planificacion.id]
            user.groups_id = [(6,0, grupos)]
            flag = False
        else:
            user = self.userid

        if not self.piloto_id:
            piloto = self.env['leulit.piloto'].create({'partner_id':self.partner_id.id})
            self.piloto_id = piloto.id
            flag = False

        self.is_alta = True
        if flag:
            raise UserError("Este alumno ya tiene el usuario y el piloto creados.")
        

    # Función para sincronizar las horas de los partes de escual con las horas de la clase rel_parte_escuela_cursos_alumno
    def sincronizar_horas(self):
        _logger.error("################### sincronizar_horas ")
        threaded_calculation = threading.Thread(target=self.run_sincronizar_horas, args=([]))
        _logger.error("################### sincronizar_horas start thread")
        threaded_calculation.start()


    def run_sincronizar_horas(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            for parte_escuela in self.env['leulit.parte_escuela'].search([]):
                lineas = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_parte_escuela','=',parte_escuela.id)])
                alumnos = []
                for linea in lineas:
                    if linea.alumno.id not in alumnos:
                        alumnos.append(linea.alumno.id)
                for alumno in alumnos:
                    suma_horas = 0
                    rel_parte_escuela = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('rel_parte_escuela','=',parte_escuela.id),('alumno','=',alumno)])
                    for linea_parte in rel_parte_escuela:
                        suma_horas += linea_parte.tiempo
                    if round(suma_horas,1) != round(parte_escuela.tiempo,1):
                        if round(suma_horas,1) > round(parte_escuela.tiempo,1):
                            diferencia = round(suma_horas,1) - round(parte_escuela.tiempo,1)
                            if diferencia > 0.1:
                                tiempo_por_linea = round(parte_escuela.tiempo,1)/len(rel_parte_escuela)
                                for linea_parte in rel_parte_escuela:
                                    linea_parte.tiempo = tiempo_por_linea
                                    self.env.cr.commit()
                        if round(suma_horas,1) < round(parte_escuela.tiempo,1):
                            diferencia = round(parte_escuela.tiempo,1) - round(suma_horas,1)
                            if diferencia > 0.1:
                                tiempo_por_linea = round(parte_escuela.tiempo,1)/len(rel_parte_escuela)
                                for linea_parte in rel_parte_escuela:
                                    linea_parte.tiempo = tiempo_por_linea
                                    self.env.cr.commit()


        _logger.error('################### set_precios_almacen fin thread')