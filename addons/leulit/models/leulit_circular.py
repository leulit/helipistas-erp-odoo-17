# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)

def condition(operand, left, right):
    if operand == '=':
        operand = '=='
    return eval(' '.join((str(left),operand,str(right))))
class leulit_circular(models.Model):
    _name           = "leulit.circular"
    _description    = "leulit_circular"
    _order          = "fecha_emision desc"
    _inherit        = ['mail.thread']
    
    
    def enviarEmail(self):
        _logger.info('='*80)
        _logger.info('INICIO enviarEmail() - Circular: "%s" (ID: %s)', self.name, self.id)
        _logger.info('Total destinatarios en historial: %s', len(self.historial_ids))
        
        # Verificar configuración de email
        
        context = self.env.context.copy()
        context.update({'fecha':self.fecha_emision,
                        'autor': self.autor_id.name,
                        'area': self.area.name,
                        'nombre': self.name,
                        'descrip': self.description
                        })
        if self.fecha_fin:
            context.update({'fecha_fin': self.fecha_fin})
        else:
            context.update({'fecha_fin': '-'})
        if self.fecha_emision:
            context.update({'fecha': self.fecha_emision})
        else:
            context.update({'fecha': '-'})
        
        # Acumular resultados de envío
        enviados_ok = []
        enviados_error = []
        
        _logger.info('Iniciando bucle de envío de emails...')
        
        for destinatario in self.historial_ids:            
            # TEMPORAL: Comentado para probar reenvío de todos los emails
            # if not destinatario.enviado:
            _logger.info('Procesando destinatario: %s (enviado=%s)', 
                        destinatario.partner_email, destinatario.enviado)
            
            context.update({'mail_to': destinatario.partner_email})
            template = self.with_context(context).env.ref("leulit.leulit_circular_template")
            _logger.info('Template email_from: %s', template.email_from or 'No configurado en template')
            _logger.info('Template email_to: %s', template.email_to or 'No configurado en template')
            try:
                _logger.info('Intentando enviar email a: %s', destinatario.partner_email)
                template.with_context(context).send_mail(self.id, force_send=True, raise_exception=True)
                # Solo marcar como enviado si fue exitoso
                destinatario.write({'enviado': True})
                enviados_ok.append(destinatario.partner_email)
                _logger.info('✓ Email enviado exitosamente a: %s', destinatario.partner_email)
            except Exception as e:
                error_msg = str(e)
                enviados_error.append({
                    'email': destinatario.partner_email,
                    'error': error_msg
                })
                _logger.error('✗ Error enviando circular "%s" (ID: %s) a %s: %s', 
                             self.name, self.id, destinatario.partner_email, error_msg)
        
        _logger.info('Bucle finalizado. Enviados OK: %s, Errores: %s', 
                    len(enviados_ok), len(enviados_error))
        
        # Mostrar resultado al usuario siempre
        if enviados_error:
            _logger.info('Caso: HAY ERRORES - Mostrando UserError con detalles')
            # Hay errores - usar UserError para mostrar detalles
            msg_partes = []
            
            if enviados_ok:
                msg_partes.append(_("✓ Emails enviados correctamente (%s):") % len(enviados_ok))
                msg_partes.append("  • " + "\n  • ".join(enviados_ok))
                msg_partes.append("")
            
            msg_partes.append(_("✗ Emails con errores (%s):") % len(enviados_error))
            for error_info in enviados_error:
                msg_partes.append(f"  • {error_info['email']}")
                msg_partes.append(f"    Error: {error_info['error']}")
            
            msg_partes.append("")
            msg_partes.append(_("Revise los logs del servidor para más detalles técnicos."))
            
            mensaje_final = "\n".join(msg_partes)
            _logger.info('Lanzando UserError con mensaje: %s', mensaje_final)
            raise UserError(mensaje_final)
        elif enviados_ok:
            _logger.info('Caso: TODO OK - Mostrando notificación de éxito')
            # Todo OK - mostrar notificación de éxito y retornar acción
            mensaje_exito = _("✓ Todos los emails se han enviado correctamente (%s):\n\n") % len(enviados_ok)
            mensaje_exito += "  • " + "\n  • ".join(enviados_ok)
            
            _logger.info('Retornando display_notification con mensaje: %s', mensaje_exito)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Envío Completado'),
                    'message': mensaje_exito,
                    'sticky': True,
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        else:
            _logger.info('Caso: NO HAY PENDIENTES - Mostrando UserError')
            # No había destinatarios pendientes
            raise UserError(_("No hay emails pendientes de enviar."))


    def create_historial_circular(self, from_onchange=False):
        if self.area:
            nuevos_historiales = []
            partner_ids_existentes = [h.partner_id.id for h in self.historial_ids if h.partner_id]
            
            if self.area.name == 'Alumnos Activos':
                alumnos_activos = self.env['leulit.alumno'].search([('activo','=',True)])
                for alumno in alumnos_activos:
                    if not alumno.userid.employee_id:
                        if alumno.partner_id and alumno.partner_id.id not in partner_ids_existentes:
                            if from_onchange:
                                # Usar comando (0, 0, vals) para crear en onchange
                                nuevos_historiales.append((0, 0, {'partner_id': alumno.partner_id.id}))
                            else:
                                self.env['leulit.historial_circular'].create({
                                    'partner_id': alumno.partner_id.id, 
                                    'circular_id': self.id
                                })
            else:
                empleados = self.env['hr.employee'].search([('department_id','=', self.area.id)])
                _logger.error("Empleados area {0}: {1}".format(self.area.name, len(empleados)))
                for empleado in empleados:
                    if empleado.user_id and empleado.user_id.partner_id:
                        if empleado.user_id.partner_id.id not in partner_ids_existentes:
                            if from_onchange:
                                # Usar comando (0, 0, vals) para crear en onchange
                                nuevos_historiales.append((0, 0, {'partner_id': empleado.user_id.partner_id.id}))
                            else:
                                self.env['leulit.historial_circular'].create({
                                    'partner_id': empleado.user_id.partner_id.id, 
                                    'circular_id': self.id
                                })
            
            if from_onchange and nuevos_historiales:
                self.historial_ids = nuevos_historiales
    

    @api.model
    def create(self, vals):
        result = super(leulit_circular, self).create(vals)
        result.create_historial_circular()
        return result


    @api.onchange('area')
    def onchange_area(self):
        self.create_historial_circular(from_onchange=True)
            
        
    @api.depends('autor_id','historial_ids')
    def _is_mine(self):
        for item in self:
            item.is_mine = False
            # Verificar si soy el autor
            if item.autor_id and item.autor_id.id == self.env.uid:
                item.is_mine = True
            # Si no soy el autor, verificar si estoy en el historial
            elif item.historial_ids:
                for historial in item.historial_ids:
                    if historial.user_id and historial.user_id.id == self.env.uid:
                        item.is_mine = True
                        break  # Salir del bucle en cuanto lo encuentre


    def _search_is_mine(self, operator, value):
        """
        Búsqueda optimizada para el campo is_mine.
        Usa consultas SQL en lugar de cargar todos los registros.
        """
        # Construir la consulta para circulares donde soy autor
        query_autor = """
            SELECT id FROM leulit_circular 
            WHERE autor_id = %s
        """
        
        # Construir la consulta para circulares donde estoy en el historial
        query_historial = """
            SELECT DISTINCT lc.id 
            FROM leulit_circular lc
            INNER JOIN leulit_historial_circular lhc ON lhc.circular_id = lc.id
            INNER JOIN res_partner rp ON rp.id = lhc.partner_id
            INNER JOIN res_users ru ON ru.partner_id = rp.id
            WHERE ru.id = %s
        """
        
        # Ejecutar las consultas
        self.env.cr.execute(query_autor, (self.env.uid,))
        ids_autor = [row[0] for row in self.env.cr.fetchall()]
        
        self.env.cr.execute(query_historial, (self.env.uid,))
        ids_historial = [row[0] for row in self.env.cr.fetchall()]
        
        # Combinar ambos conjuntos de IDs (sin duplicados)
        ids = list(set(ids_autor + ids_historial))
        
        # Aplicar el operador
        if operator == '=' and value:
            # is_mine = True -> devolver circulares donde estoy
            return [('id', 'in', ids)] if ids else [('id', '=', False)]
        elif operator == '=' and not value:
            # is_mine = False -> devolver circulares donde NO estoy
            return [('id', 'not in', ids)] if ids else []
        elif operator == '!=':
            # Invertir la lógica
            if value:
                return [('id', 'not in', ids)] if ids else []
            else:
                return [('id', 'in', ids)] if ids else [('id', '=', False)]
        
        # Por defecto, no devolver nada
        return [('id', '=', False)]


    @api.depends('historial_ids')
    def _pendiente(self):
        for item in self:
            item.pendiente_todos = False
            for historial in item.historial_ids:
                if not historial.recibido or not historial.leido or not historial.entendido:
                    item.pendiente_todos = True
                    break  # Salir en cuanto encuentre uno pendiente


    @api.depends('historial_ids')
    def _pendiente_mine(self):
        for item in self:
            item.pendiente = False
            for historial in item.historial_ids:
                if historial.user_id and historial.user_id.id == self.env.uid:
                    if not historial.recibido or not historial.leido or not historial.entendido:
                        item.pendiente = True
                    break  # Solo hay un historial por usuario, salir


    def _search_pendiente(self, operator, value):
        """
        Búsqueda optimizada para circulares pendientes del usuario actual.
        """
        # Consulta SQL optimizada
        if value:
            # pendiente = True -> buscar circulares donde el usuario tiene tareas pendientes
            query = """
                SELECT DISTINCT lc.id 
                FROM leulit_circular lc
                INNER JOIN leulit_historial_circular lhc ON lhc.circular_id = lc.id
                INNER JOIN res_partner rp ON rp.id = lhc.partner_id
                INNER JOIN res_users ru ON ru.partner_id = rp.id
                WHERE ru.id = %s
                AND (lhc.recibido = FALSE OR lhc.leido = FALSE OR lhc.entendido = FALSE)
            """
        else:
            # pendiente = False -> buscar circulares donde el usuario completó todo
            query = """
                SELECT DISTINCT lc.id 
                FROM leulit_circular lc
                INNER JOIN leulit_historial_circular lhc ON lhc.circular_id = lc.id
                INNER JOIN res_partner rp ON rp.id = lhc.partner_id
                INNER JOIN res_users ru ON ru.partner_id = rp.id
                WHERE ru.id = %s
                AND lhc.recibido = TRUE 
                AND lhc.leido = TRUE 
                AND lhc.entendido = TRUE
            """
        
        self.env.cr.execute(query, (self.env.uid,))
        ids = [row[0] for row in self.env.cr.fetchall()]
        
        # Aplicar operador
        if operator == '=':
            return [('id', 'in', ids)] if ids else [('id', '=', False)]
        elif operator == '!=':
            return [('id', 'not in', ids)] if ids else []
        
        return [('id', '=', False)]


    @api.depends('fecha_fin')
    def _caducada(self):
        for item in self:
            if item.fecha_fin:
                hoy = datetime.now().date()
                # Caducada si fecha_fin es anterior a hoy
                item.caducada = item.fecha_fin < hoy
            else:
                item.caducada = False


    def _search_caducada(self, operator, value):
        """
        Búsqueda optimizada para circulares caducadas.
        """
        hoy = datetime.now().date()
        
        if operator == '=' and value:
            # caducada = True -> fecha_fin < hoy
            return [('fecha_fin', '<', hoy), ('fecha_fin', '!=', False)]
        elif operator == '=' and not value:
            # caducada = False -> fecha_fin >= hoy O fecha_fin es NULL
            return ['|', ('fecha_fin', '>=', hoy), ('fecha_fin', '=', False)]
        elif operator == '!=' and value:
            # caducada != True -> fecha_fin >= hoy O fecha_fin es NULL
            return ['|', ('fecha_fin', '>=', hoy), ('fecha_fin', '=', False)]
        elif operator == '!=' and not value:
            # caducada != False -> fecha_fin < hoy
            return [('fecha_fin', '<', hoy), ('fecha_fin', '!=', False)]
        
        return [('id', '=', False)]
        

    name = fields.Char("Nombre", required=True)
    description = fields.Html("Descripción",  required=True)
    fecha_emision = fields.Date("Fecha de emisión", required=False,default=fields.Date.context_today)
    fecha_fin = fields.Date("Fecha fin", required=False)
    estado = fields.Selection([('valido','Válido'),('no_valido','No válido')],"Estado",  required=False)
    area = fields.Many2one('hr.department','Área',ondelete='restrict')
    area_name = fields.Char(related='area.name',string='Area',store=False)
    autor_id = fields.Many2one('res.users','Autor',ondelete='restrict', readonly=True, default=lambda self: self.env.uid)
    historial_ids = fields.One2many('leulit.historial_circular', 'circular_id', string='Circular')
    is_mine = fields.Boolean(compute='_is_mine',string='Asignada',store=False,search=_search_is_mine)
    pendiente = fields.Boolean(compute='_pendiente_mine',string='Pendiente',store=False,search=_search_pendiente)
    pendiente_todos = fields.Boolean(compute='_pendiente',string='',store=False)
    caducada = fields.Boolean(compute='_caducada',string='Caducada',store=False,search=_search_caducada)
    tipo = fields.Selection([('1', 'Genérica'),('2','Seguridad'),('3','Informativa')],'Tipo')
    