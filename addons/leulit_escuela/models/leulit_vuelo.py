# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class leulit_vuelo(models.Model):
    _inherit = "leulit.vuelo"


    def wizard_add_parte_escuela(self):
        _logger.info(
            "[Escuela] Opening 'Añadir Silabus' wizard for vuelo ids=%s user=%s",
            self.ids,
            self.env.user.id,
        )
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_escuela.leulit_20210128_1141_form')
        view_id = view_ref and view_ref[1] or False
        for item in self:
            if item.alumno or item.verificado:
                aluveri = None
                if item.verificado:
                    aluveri = item.verificado.partner_id.getAlumno()
                    # Diagnóstico: si verificado existe pero getAlumno() no devuelve nada, levantar excepción con detalles
                    if not aluveri:
                        partner = item.verificado.partner_id
                        alumnos_by_partner = self.env['leulit.alumno'].search([('partner_id', '=', partner.id)])
                        alumnos_by_piloto = self.env['leulit.alumno'].search([('piloto_id', '=', item.verificado.id)])
                        alumnos_by_partner_sudo = self.env['leulit.alumno'].sudo().search([('partner_id', '=', partner.id)])
                        alumnos_by_piloto_sudo = self.env['leulit.alumno'].sudo().search([('piloto_id', '=', item.verificado.id)])

                        msg = (
                            "No se pudo resolver el Alumno desde 'verificado'.\n\n"
                            f"Vuelo ID: {item.id}\n"
                            f"Verificado (leulit.piloto) ID: {item.verificado.id if item.verificado else None} | Nombre: {item.verificado.name if item.verificado else None}\n"
                            f"Partner de Verificado (res.partner) ID: {partner.id if partner else None} | Nombre: {partner.name if partner else None}\n\n"
                            "Detalles de búsqueda visibles para el usuario actual:\n"
                            f"- leulit.alumno por partner_id={partner.id}: {alumnos_by_partner.ids}\n"
                            f"- leulit.alumno por piloto_id={item.verificado.id}: {alumnos_by_piloto.ids}\n\n"
                            "Detalles de búsqueda con sudo (sin reglas de registro):\n"
                            f"- leulit.alumno por partner_id={partner.id}: {alumnos_by_partner_sudo.ids}\n"
                            f"- leulit.alumno por piloto_id={item.verificado.id}: {alumnos_by_piloto_sudo.ids}\n\n"
                            f"Usuario actual: id={self.env.user.id} login={self.env.user.login}\n"
                        )
                        raise UserError(_(msg))
                if item.alumno:
                    aluveri = item.alumno.partner_id.getAlumno()
                    # Diagnóstico: si el alumno del vuelo no se resuelve vía su partner
                    if not aluveri or aluveri != item.alumno.id:
                        partner = item.alumno.partner_id
                        alumno_record = item.alumno
                        alumnos_by_partner = self.env['leulit.alumno'].search([('partner_id', '=', partner.id)])
                        alumnos_by_partner_sudo = self.env['leulit.alumno'].sudo().search([('partner_id', '=', partner.id)])

                        msg = (
                            "El Alumno del vuelo no se corresponde con el partner indicado.\n\n"
                            f"Vuelo ID: {item.id}\n"
                            f"Alumno en vuelo (leulit.alumno) ID: {alumno_record.id} | Nombre: {alumno_record.name}\n"
                            f"Partner del alumno (res.partner) ID: {partner.id if partner else None} | Nombre: {partner.name if partner else None}\n"
                            f"getAlumno(partner) devolvió: {aluveri}\n\n"
                            "Detalles de búsqueda visibles para el usuario actual:\n"
                            f"- leulit.alumno por partner_id={partner.id}: {alumnos_by_partner.ids}\n\n"
                            "Detalles de búsqueda con sudo (sin reglas de registro):\n"
                            f"- leulit.alumno por partner_id={partner.id}: {alumnos_by_partner_sudo.ids}\n\n"
                            f"Usuario actual: id={self.env.user.id} login={self.env.user.login}\n"
                        )
                        raise UserError(_(msg))

                profesor_id = False
                source_piloto = None
                if item.piloto_supervisor_id:
                    source_piloto = item.piloto_supervisor_id
                    profesor_id = source_piloto.partner_id.getProfesor()
                else:
                    source_piloto = item.piloto_id
                    profesor_id = source_piloto.partner_id.getProfesor()

                # Diagnóstico: si no se resolvió profesor desde el piloto seleccionado
                if not profesor_id and source_piloto:
                    partner_prof = source_piloto.partner_id
                    profesores_by_partner = self.env['leulit.profesor'].search([('partner_id', '=', partner_prof.id)])
                    profesores_by_partner_sudo = self.env['leulit.profesor'].sudo().search([('partner_id', '=', partner_prof.id)])

                    msg = (
                        "No se pudo resolver el Profesor desde el piloto indicado.\n\n"
                        f"Vuelo ID: {item.id}\n"
                        f"Piloto origen: ID={source_piloto.id} | Nombre={source_piloto.name}\n"
                        f"Partner del piloto (res.partner): ID={partner_prof.id if partner_prof else None} | Nombre={partner_prof.name if partner_prof else None}\n\n"
                        "Detalles de búsqueda visibles para el usuario actual:\n"
                        f"- leulit.profesor por partner_id={partner_prof.id}: {profesores_by_partner.ids}\n\n"
                        "Detalles de búsqueda con sudo (sin reglas de registro):\n"
                        f"- leulit.profesor por partner_id={partner_prof.id}: {profesores_by_partner_sudo.ids}\n\n"
                        f"Usuario actual: id={self.env.user.id} login={self.env.user.login}\n"
                    )
                    raise UserError(_(msg))

                _logger.info(
                    "[Escuela] wizard_add_parte_escuela computed ids: vuelo=%s alumno=%s verificado=%s profesor_id=%s aluveri=%s",
                    item.id,
                    item.alumno.id if item.alumno else None,
                    item.verificado.id if item.verificado else None,
                    profesor_id,
                    aluveri,
                )

                context = {
                    'default_vuelo_id'   : item.id,
                    'default_fecha'      : item.fechavuelo,
                    'default_hora_start' : item.horasalida,
                    'default_tiempo'     : item.tiempoprevisto if item.horallegada <= item.horasalida else item.tiemposervicio,
                    'default_hora_end'   : item.horallegadaprevista if item.horallegada <= item.horasalida else item.horallegada,
                }
                # Solo incluir por defecto cuando existan IDs válidos
                if profesor_id:
                    context['default_profesor_id'] = profesor_id
                if aluveri:
                    # Para Many2many, usar comando (6, 0, ids) como default
                    context['default_rel_alumnos'] = [(6, 0, [aluveri])]
                if item.parte_escuela_id:
                    context.update({'default_parte_escuela_id' : item.parte_escuela_id.id})

                # Log de contexto saneado para depuración
                try:
                    ctx_log = {k: (v if not isinstance(v, (list, tuple)) else v) for k, v in context.items()}
                    _logger.info("[Escuela] Wizard context prepared: %s", ctx_log)
                except Exception:
                    _logger.exception("[Escuela] Error logging wizard context")

                return_options = {
                    'type'           : 'ir.actions.act_window',
                    'name'           : 'Silabus',
                    'res_model'      : 'leulit.popup_rel_parte_escuela_cursos_alumnos',
                    'view_type'      : 'form',
                    'view_mode'      : 'form',
                    'view_id'        : view_id,
                    'target'         : 'new',
                    'nodestroy'      : True,
                    'context'        : context,
                }

                _logger.info("[Escuela] Returning wizard action for vuelo=%s", item.id)
                return return_options
            else:
                raise UserError(_('Debe indicarse el verificado/alumno antes de indicar silabus'))


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

    
    def wizardSetPrevuelo(self):
        if self.parte_escuela_id:
            self.parte_escuela_id.unlink()
        return super(leulit_vuelo, self).wizardSetPrevuelo()
    

    @api.depends('piloto_id','alumno')
    def _get_is_doblemando(self):
        for item in self:
            item.doblemando = False
            if item.piloto_id and item.alumno:
                if item.piloto_id.getPartnerId() != item.alumno.getPartnerId():
                    item.doblemando = True

    @api.depends('piloto_id','operador','vuelo_tipo_line')
    def _get_semaforo_pf(self):
        for item in self:
            item.semaforo_pf_piloto = 'green'
            item.semaforo_pf_operador = 'green'
            if item.piloto_id:
                tripulante_alumno = self.env['leulit.alumno'].search([('partner_id','=',item.piloto_id.getPartnerId())])
                tipo_formacion = self.env['leulit.vuelostipo'].search([('name','=','Formación interna')])
                if any(tipo_formacion.id == tipo.id for tipo in item.vuelo_tipo_line.vuelo_tipo_id):
                    domain = [('alumno','=',tripulante_alumno.id),('inactivo','=',False)]
                else:
                    domain = [('alumno','=',tripulante_alumno.id),('inactivo','=',False),('tipo_helicoptero','=',item.helicoptero_id.modelo.tipo)]
                pfs = self.env['leulit.perfil_formacion'].search(domain)
                if len(pfs) > 0:
                    exists = False
                    for pf in pfs:
                        if any(pf.vuelo_tipo_id.id == tipo.id for tipo in item.vuelo_tipo_line.vuelo_tipo_id):
                            exists = True
                            for curso in pf.cursos:
                                if curso.semaforo_dy == 'red':
                                    item.semaforo_pf_piloto = 'red'
                            for accion in pf.acciones_new:
                                if accion.semaforo_dy == 'red':
                                    item.semaforo_pf_piloto = 'red'
                    if not exists:
                        item.semaforo_pf_piloto = 'N/A'
                else:
                    item.semaforo_pf_piloto = 'N/A'
                if item.ruta_id and item.ruta_id.water_zone:
                    for pf in self.env['leulit.perfil_formacion'].search([('alumno','=',tripulante_alumno.id),('inactivo','=',False),('water_zone','=',True)]):
                        for curso in pf.cursos:
                            if curso.semaforo_dy == 'red':
                                item.semaforo_pf_piloto = 'red'
                        for accion in pf.acciones_new:
                            if accion.semaforo_dy == 'red':
                                item.semaforo_pf_piloto = 'red'
            else:
                item.semaforo_pf_piloto = 'N/A'
            if item.operador:
                tripulante_alumno_op = self.env['leulit.alumno'].search([('partner_id','=',item.operador.getPartnerId())])
                pfs = self.env['leulit.perfil_formacion'].search([('alumno','=',tripulante_alumno_op.id),('inactivo','=',False),('operador','=',True)])
                if pfs:
                    exists = False
                    for pf in pfs:
                        if any(pf.vuelo_tipo_id.id == tipo.id for tipo in item.vuelo_tipo_line.vuelo_tipo_id):
                            exists = True
                            for curso in pf.cursos:
                                if curso.semaforo_dy == 'red':
                                    item.semaforo_pf_operador = 'red'
                            for accion in pf.acciones_new:
                                if accion.semaforo_dy == 'red':
                                    item.semaforo_pf_operador = 'red'
                    if not exists:
                        item.semaforo_pf_operador = 'N/A'
                else:
                    item.semaforo_pf_operador = 'N/A'
            else:
                item.semaforo_pf_operador = 'N/A'


    parte_escuela_id = fields.Many2one('leulit.parte_escuela', 'Parte escuela',ondelete='set null')
    silabus_ids = fields.One2many(comodel_name='leulit.rel_parte_escuela_cursos_alumnos', inverse_name='rel_vuelo', string='Silabus')
    alumno = fields.Many2one('leulit.alumno', 'Alumno',domain="[('piloto_id', '!=', False)]")
    peso_alumno = fields.Float(related='alumno.peso_piloto',string='Peso alumno')
    foto_alumno = fields.Binary(related='alumno.image_128',string='Foto empleado',store=False)
    act_vuelo_id = fields.Many2one('leulit.actividad_vuelo', 'Actividad Vuelo')
    comentario_escuela = fields.Text('Comentario Parte de Escuela')
    valoracion_escuela = fields.Selection(_get_valoracion_options,'Valoración Parte de Escuela')
    doblemando = fields.Boolean(compute=_get_is_doblemando, string='Doble mando', store=True)
    semaforo_pf_piloto = fields.Char(compute=_get_semaforo_pf, string='Perfil Formación', store=False)
    semaforo_pf_operador = fields.Char(compute=_get_semaforo_pf, string='Perfil Formación', store=False)


    def update_pf_acciones(self):
        o_pf = self.env['leulit.perfil_formacion']
        o_alumno = self.env['leulit.alumno']
        ids_partners = list({partner_id for partner_id in [self.piloto_id.getPartnerId() if self.piloto_id else None, self.verificado.getPartnerId() if self.verificado else None, self.alumno.getPartnerId() if self.alumno else None] if partner_id})
        tripulantes_alumno = o_alumno.search([('partner_id', 'in', ids_partners)])
        for tripulante_alumno in tripulantes_alumno:
            piloto_tripulante_id = self.env['res.partner'].search([('id','=',tripulante_alumno.getPartnerId())]).getPiloto()
            # 3 Tomas
            fecha_3_tomas = False
            pf_accion_con_3tomas = False
            night_fecha_3_tomas = False
            night_pf_accion_con_3tomas = False

            perfiles_formacion = o_pf.search([('alumno','=',tripulante_alumno.id),('inactivo','=',False),('tipo_helicoptero','=',self.helicoptero_tipo)])
            for pf in perfiles_formacion:
                for accion in pf.acciones_new:
                    if accion.accion.landings_day:
                        fecha_3_tomas = accion.last_done_date
                        pf_accion_con_3tomas = accion
                    if accion.accion.landings_night:
                        night_fecha_3_tomas = accion.last_done_date
                        night_pf_accion_con_3tomas = accion
                if fecha_3_tomas and night_fecha_3_tomas:
                    break

            if fecha_3_tomas:
                contador_landings = 0
                for vuelo in self.search([('fechavuelo','>', fecha_3_tomas),('helicoptero_tipo','=',self.helicoptero_tipo),'|','|',('piloto_id','=',piloto_tripulante_id),('verificado', '=', piloto_tripulante_id),('alumno', '=', tripulante_alumno.id)]):
                    contador_landings += vuelo.landings
                if contador_landings >= 3:
                    accion_last = self.env['leulit.pf_accion_last_done'].sudo().create({'pf_accion': pf_accion_con_3tomas.id, 'done_date': self.fechavuelo, 'name': pf_accion_con_3tomas.accion.name,'actualizartodos': True})
                    try:
                        accion_last.sudo().do_done_course()
                    except Exception as e:
                        raise UserError(_('Error al actualizar las acciones 1: %s', e))
            if night_fecha_3_tomas:
                contador_nightlandings = 0
                for vuelo in self.search([('fechavuelo','>', night_fecha_3_tomas),('helicoptero_tipo','=',self.helicoptero_tipo),'|','|',('piloto_id','=',piloto_tripulante_id),('verificado', '=', piloto_tripulante_id),('alumno', '=', tripulante_alumno.id)]):
                    contador_nightlandings += vuelo.nightlandings
                if contador_nightlandings >= 3:
                    accion_last = self.env['leulit.pf_accion_last_done'].sudo().create({'pf_accion': night_pf_accion_con_3tomas.id, 'done_date': self.fechavuelo, 'name': night_pf_accion_con_3tomas.accion.name,'actualizartodos': True})
                    try:
                        accion_last.sudo().do_done_course()
                    except Exception as e:
                        raise UserError(_('Error al actualizar las acciones 2: %s', e))

            # Experiencia reciente
            vuelo_tipos_sop = [] 
            for vuelo_tipo in self.env['leulit.vuelostipo'].search([('tipo_trabajo','=','Trabajo Aereo')]):
                if any(vuelo_tipo.id == tipo.id for tipo in self.vuelo_tipo_line.vuelo_tipo_id):
                    if 'SOP02' in vuelo_tipo.name:
                        vuelo_tipos_sop.append(self.env['leulit.vuelostipo'].search([('name','=','SPO SOP01 Fotografía y filmación')]).id)
                    if 'SOP05' in vuelo_tipo.name:
                        vuelo_tipos_sop.append(self.env['leulit.vuelostipo'].search([('name','=','SPO SOP04 Publicidad aérea')]).id)
                    if 'SOP06' in vuelo_tipo.name:
                        vuelo_tipos_sop.append(self.env['leulit.vuelostipo'].search([('name','=','SPO SOP01 Fotografía y filmación')]).id)
                        vuelo_tipos_sop.append(self.env['leulit.vuelostipo'].search([('name','=','SPO SOP02 Pipeline')]).id)
                        vuelo_tipos_sop.append(vuelo_tipo.id)
            tipos_usados = []
            for pf in o_pf.search([('alumno','=',tripulante_alumno.id),('inactivo','=',False),('tipo_helicoptero','!=',False),('vuelo_tipo_id','in',vuelo_tipos_sop)]):
                if pf.vuelo_tipo_id.id not in tipos_usados:
                    for accion in pf.acciones_new:
                        if accion.accion.experiencia_reciente:
                            accion_last = self.env['leulit.pf_accion_last_done'].sudo().create({'pf_accion': accion.id, 'done_date': self.fechavuelo, 'name': accion.accion.name, 'actualizartodos': True})
                            try:
                                accion_last.sudo().do_done_course()
                            except Exception as e:
                                raise UserError(_('Error al actualizar las acciones 3: %s', e))
                            tipos_usados.append(pf.vuelo_tipo_id.id)
                            continue


    # El número de AL/PA/PAE/PO cambia automáticamente si hay alumno
    @api.onchange('alumno')
    def cambio_numpae_alumno(self):
        if self.alumno: 
            self.numpae = 1
        else:
            self.numpae = 0
    