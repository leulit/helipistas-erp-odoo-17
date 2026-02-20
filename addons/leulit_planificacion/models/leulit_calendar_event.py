# -*- encoding: utf-8 -*-

from re import A
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
import pytz
from odoo.addons.leulit import utilitylib
import threading
import time


_logger = logging.getLogger(__name__)


class leulit_calendar_event(models.Model):
    _name = 'calendar.event'
    _inherit = 'calendar.event'


    @api.model_create_multi
    def create(self, vals_list):
        # Iterar sobre cada conjunto de valores
        for vals in vals_list:
            self._check_event_permissions(vals)  # Comprobar permisos para cada registro
        return super(leulit_calendar_event, self).create(vals_list)


    def _resource_fields_values(self, resource_fields):
        resource_commands = []
        resource_commands += [
            [0, 0, dict(resource=resource_field.resource.id,rol=resource_field.rol,work_hours=resource_field.work_hours)]
            for resource_field in resource_fields
        ]
        return resource_commands


    def unlink(self):
        for item in self:
            if self.env.uid != 14:
                raise UserError('Intento de eliminar evento no autorizado.')
        return super().unlink()


    def write(self, vals):
        if self.env.context.get('skip_validation', False):
            return super(leulit_calendar_event, self).write(vals)
        for record in self:
            record._check_event_permissions(vals)
        return super(leulit_calendar_event, self).write(vals)


    def _check_event_permissions(self, vals):
        """Comprueba permisos de creación/escritura según los roles del usuario."""
        user = self.env.user

        # Obtener el tipo de evento actual (desde el registro si está editando, o desde vals si está creando)
        # temporada alta (Mayo, Junio, Julio, Agosto y septiembre)
        if 'start' in vals:
            event_start = fields.Datetime.from_string(vals['start'])  # Fecha de inicio del evento
            event_end = fields.Datetime.from_string(vals['stop'])  # Fecha de fin del evento
        else:
            event_start = self.start
            event_end = self.stop
            
        if (5 <= event_start.month <= 9) or (5 <= event_end.month <= 9):
            if 'type_event' in vals:
                type_event = self.env['leulit.tipo_planificacion'].browse(vals['type_event'])
            else:
                type_event = self.type_event

            # Verificar si el tipo de evento es 'Ocupado' y si el usuario tiene el grupo adecuado
            if type_event.name == 'No disponible (vacaciones, ausencias, etc..)' and not user.has_group('leulit.ROperaciones_gestor') and not user.has_group('leulit.RTaller_base') and not user.has_group('leulit_tarea.RT_administrador'):
                raise exceptions.AccessError(_("No tienes permisos para crear o editar eventos de tipo 'No disponible' en temporada alta."))

        # Si el usuario tiene el rol de manager, puede crear/escribir en todos los eventos
        if user.has_group('leulit_planificacion.RPlanificacion_manager'):
            return

        # Si el usuario tiene el rol de "all", verifica si está en los participantes
        if user.has_group('leulit_planificacion.RPlanificacion_all'):
            # Obtener los participantes existentes
            existing_participants = set(self.partner_ids.ids) if self else set()

            # Manejar cambios en partner_ids desde vals
            if 'partner_ids' in vals:
                commands = vals['partner_ids']
                if isinstance(commands, list):
                    for command in commands:
                        if command[0] == 6:  # Reemplazar todos los IDs
                            existing_participants = set(command[2])
                        elif command[0] == 4:  # Añadir un ID
                            existing_participants.add(command[1])
                        elif command[0] == 3:  # Quitar un ID
                            existing_participants.discard(command[1])
                        elif command[0] == 5:  # Limpiar todos los IDs
                            existing_participants = set()

            # Verificar si el usuario actual está en la lista combinada de participantes
            if user.partner_id.id not in existing_participants:
                raise exceptions.AccessError(_("No puedes crear ni editar eventos si no eres participante."))

            return  # Si está permitido, se detiene aquí

        # Si el usuario no tiene ninguno de los dos roles, no puede crear/escribir
        raise exceptions.AccessError(_("No tienes permisos para crear ni editar eventos."))


    def cancelar_evento(self):
        values = {
            'name': '[CANCELADO] {0}'.format(self.name),
            'cancelado': True,
            'cancelado_por': self.env.uid,
            'cancelado_date': utilitylib.getStrToday()
        }
        self.write(values)
        # self.send_mail('CANCELADO')


    def cancelar_evento_popup(self):
        self.ensure_one()
        view = self.env.ref('leulit_planificacion.leulit_20220314_1649_form',raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancelar evento',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'res_id': self.id,
        }


    @api.constrains('resource_fields', 'partner_ids', 'start', 'stop', 'duration')
    def validate_event_constraints(self):
        if self.env.context.get('skip_validation', False):
            return
        for event in self:
            if not event.cancelado:
                if not event.allday:
                    # Validar superposición de recursos
                    if event.resource_fields:
                        self._validate_resources_overlap(event)
                    elif event.recurrence_id and not event.resource_fields:
                        self._set_resources_from_recurrence(event)
                    
                    # Validar superposición de participantes
                    if event.partner_ids:
                        self._validate_participants_overlap(event)
                    
                    # Actualizar disponibilidad de recursos
                    self._update_resource_availability(event)
                else:
                    if event.resource_fields:
                        self._validate_resources_overlap(event)
                    # Manejar el caso de eventos de todo el día
                    if event.recurrence_id and not event.resource_fields:
                        self._set_resources_from_recurrence(event)


    def _validate_resources_overlap(self, event):
        resources = [res.resource.id for res in event.resource_fields]
        overlap = self._check_overlaps(
            event.id, 
            resources, 
            event.start, 
            event.stop, 
            field='resource'
        )
        if overlap['error']:
            raise ValidationError(
                _('Existe solapamiento de fechas para el recurso: %s' % overlap['mensaje'])
            )


    def _validate_participants_overlap(self, event):
        participant_ids = event.partner_ids.ids
        overlap = self._check_overlaps(
            event.id, 
            participant_ids, 
            event.start, 
            event.stop, 
            field='participant'
        )
        if overlap['error']:
            raise ValidationError(
                _('Existe solapamiento de fechas para el participante: %s' % overlap['mensaje'])
            )


    def _check_overlaps(self, event_id, ids, start_date, end_date, field):
        """
        Comprueba si hay solapamientos para un conjunto de IDs en un rango de fechas.
        :param event_id: ID del evento actual (se excluye de la búsqueda)
        :param ids: Lista de IDs a verificar (pueden ser recursos o participantes)
        :param start_date: Fecha de inicio del evento
        :param end_date: Fecha de fin del evento
        :param field: Campo a verificar ('resource' o 'participant')
        :return: Diccionario con el estado de error y mensaje
        """
        result = {'error': False, 'mensaje': ''}
        
        # Configuración según el campo a verificar
        if field == 'resource':
            table = 'leulit_event_resource'
            column = 'resource'
            event_column = 'event'
            allday_condition = ''
        elif field == 'participant':
            table = 'calendar_event_res_partner_rel'
            column = 'res_partner_id'
            event_column = 'calendar_event_id'
            allday_condition = 'AND ce.allday = FALSE '
        else:
            raise ValueError("Invalid field value. Expected 'resource' or 'participant'.")

        # Verificación para cada ID
        for item_id in ids:
            sql = """
                SELECT
                    ce.id
                FROM {table} le
                INNER JOIN calendar_event ce ON le.{event_column} = ce.id
                WHERE ce.cancelado != TRUE 
                AND ce.id != %s 
                AND le.{column} = %s
                {allday_condition}
                AND (ce.start, ce.stop) OVERLAPS (%s, %s)
            """.format(table=table, column=column, event_column=event_column, allday_condition=allday_condition)
            self._cr.execute(sql, (event_id, item_id, start_date, end_date))
            rows = self._cr.fetchall()

            if rows:
                # Identificar el objeto conflictivo y el evento
                obj = self.env['leulit.resource'].browse(item_id) if field == 'resource' else self.env['res.partner'].browse(item_id)
                conflicting_event = self.env['calendar.event'].browse(rows[0][0])
                
                # Preparar el resultado de error
                result['error'] = True
                result['mensaje'] = 'Solapamiento en {} "{}" con el evento "{}"'.format(
                    'recurso' if field == 'resource' else 'participante', obj.name, conflicting_event.name
                )
                break

        return result


    def _set_resources_from_recurrence(self, event):
        recurrence = self.env['calendar.recurrence'].browse(event.recurrence_id.id)
        # Recoge los valores sin escribir directamente
        new_values = {
            'resource_fields': self._resource_fields_values(recurrence.base_event_id.resource_fields)
        }
        
        # Aplica los cambios una vez que la validación ha terminado
        event.with_context(skip_validation=True).write(new_values)
        # event.resource_fields = self._resource_fields_values(recurrence.base_event_id.resource_fields)
        event.type_event = recurrence.base_event_id.type_event.id

    def _update_resource_availability(self, event):
        start_hour = utilitylib.leulit_str_to_float_time(
            '{0}:{1}'.format(event.start.hour, event.start.minute)
        )
        stop_hour = utilitylib.leulit_str_to_float_time(
            '{0}:{1}'.format(event.stop.hour, event.stop.minute)
        )
        sql = """
            UPDATE
                leulit_event_resource
            SET
                availability_hours = %s,
                date = %s,
                date_deadline = %s,
                fecha_ini = %s,
                fecha_fin = %s,
                hora_ini = %s,
                hora_fin = %s
            WHERE
                event = %s
        """
        self._cr.execute(sql, (
            event.duration, 
            event.start, 
            event.stop, 
            event.start.date(), 
            event.stop.date(), 
            start_hour, 
            stop_hour, 
            event.id
        ))


    def _get_tipos(self):
        return utilitylib.leulit_get_tipos_planificacion()


    def _uid_in_resources(self):
        for item in self:
            valor = False
            if item.resource_fields:
                for resource in item.resource_fields:
                    if resource.resource:
                        if resource.resource.user:
                            if self.env.user.id == resource.resource.user.id:
                                valor = True
                                break
            item.uid_in_resources = valor


    def _uid_in_resources_search(self, operator, value):
        query = """
            SELECT DISTINCT ce.id 
            FROM calendar_event ce
            WHERE EXISTS (
                SELECT 1
                FROM leulit_event_resource ler
                JOIN leulit_resource lr ON ler.resource = lr.id
                WHERE ler.event = ce.id
                AND lr.user = %s
            )
        """
        self.env.cr.execute(query, (self.env.user.id,))
        event_ids = [r[0] for r in self.env.cr.fetchall()]
        
        if event_ids:
            return [('id', 'in', event_ids)]
        return [('id', '=', False)]
    

    def _get_historic_lines(self):
        for item in self:
            item.historic_lines = self.env['auditlog.log'].search([('model_model', '=', 'calendar.event'),('res_id','=',item.id)])


    @api.onchange('type_event')
    def _onchange_type_event(self):
        if self.type_event:
            self.equipamientos_ids = self.type_event.equipamientos_ids


    @api.model
    def _default_partners(self):
        """ When active_model is res.partner, the current partners should be attendees """
        partners = self.env.user.partner_id
        active_id = self._context.get('active_id')
        if self._context.get('active_model') == 'res.partner' and active_id:
            if active_id not in partners.ids:
                partners |= self.env['res.partner'].browse(active_id)
        return partners
    

    @api.depends('partner_ids')
    @api.depends_context('uid')
    def _compute_user_can_edit(self):
        for event in self:
            editor_candidates = set(event.partner_ids.user_ids + event.user_id)
            if event._origin:
                editor_candidates |= set(event._origin.partner_ids.user_ids)
            # Administradores y usuarios del grupo de planificación pueden editar eventos no privados
            if (
                self.env.user.has_group('base.group_system') or
                self.env.user.has_group('leulit_planificacion.RPlanificacion_manager')
            ) and event.privacy != 'private':
                editor_candidates.add(self.env.user)
            event.user_can_edit = self.env.user in editor_candidates


    partner_ids = fields.Many2many('res.partner', 'calendar_event_res_partner_rel', string='Attendees', default=_default_partners, domain="[('user_ids', '!=', False)]")
    resource_fields = fields.One2many(comodel_name='leulit.event_resource', inverse_name='event', string='Recurso')
    create_uid = fields.Integer(string='Creador')
    write_uid = fields.Integer(string='Modificador')
    tipo = fields.Selection(selection=_get_tipos, string='Tipo Remove', required=False)
    type_event = fields.Many2one(comodel_name='leulit.tipo_planificacion', string='Tipo', required=True)
    tipo_vuelo = fields.Boolean(related='type_event.is_vuelo', string='Tipo vuelo')
    equipamientos_ids = fields.Many2many(comodel_name='leulit.equipamientos_planificacion', relation='leulit_equipamientos_evento', column1='evento_id', column2='equipamiento_id', string='Equipamientos')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Presupuesto', domain=[('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)])
    uid_in_resources = fields.Boolean(compute="_uid_in_resources", string="User in evento", search="_uid_in_resources_search")
    documentos = fields.Many2many('ir.attachment', 'leulit_calendar_rel', 'calendar_rel', 'doc_rel','Documentos')
    localizaciones = fields.Many2many('leulit.ruta_punto','leulit_evento_punto_rel','evento_id','punto_id','Localizaciones')
    min_cloud_height = fields.Float(string='Base de nubes (ft)', default=1000)
    # TAREA
    no_modificar = fields.Boolean(string='Prioritario',default=False)
    cancelado = fields.Boolean(string='Cancelado', default=False)
    motivo_cancelacion = fields.Text(string='Motivo cancelación')
    cancelado_por = fields.Many2one(comodel_name='res.users', string='Cancelado por')
    cancelado_date = fields.Date(string='Fecha cancelación')
    write_uid = fields.Many2one(comodel_name='res.users', string='Modificado por', readonly=True)
    create_uid = fields.Many2one(comodel_name='res.users', string='Creado por', readonly=True)
    create_date = fields.Datetime(string='Fecha creación', readonly=True)
    write_date = fields.Datetime(string='Fecha modificación', readonly=True)
    ## CONEXIÓN CON GOOGLE
    google_event_id = fields.Char(string='Google Calendar Event ID', default=False)
    google_sequence = fields.Integer(string='Sequence for update', default=0)
    ## Audit Log
    historic_lines = fields.One2many(compute=_get_historic_lines, comodel_name='auditlog.log', string='Lineas historico', readonly=True)
    task_id = fields.Many2one(comodel_name='project.task', string='Tarea')


    def open_task(self):
        self.ensure_one()
        if not self.task_id:
            raise UserError('El evento no tiene asociada ninguna tarea.')
        return {
            'name': 'Tarea',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.task_id.id,
            'target': 'current',
        }

