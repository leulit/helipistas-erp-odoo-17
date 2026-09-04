# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class leulitDocumento(models.Model):
    """
    Documento unificado colgado del partner_id.

    Como leulit.alumno, leulit.piloto, leulit.operador y leulit.mecanico son
    _inherits de res.partner, todos comparten el mismo partner_id: un
    documento subido desde cualquiera de esas fichas queda visible en todas
    las demás fichas de esa misma persona, sin depender del acceso al menú
    de Contactos.
    """
    _name = "leulit.documento"
    _description = "leulit_documento"
    _order = "date desc, id desc"

    #  Función para ver si es valido el documento,
    #  mira si la fecha de hoy es mayor o igual a la fecha de caducidad,
    #  en el caso de que exista, en el caso contrario, siempre será valido.
    @api.depends('expiration_date')
    def _get_valido(self):
        for item in self:
            item.valid = True
            if item.expiration_date:
                if datetime.now().date() >= item.expiration_date:
                    item.valid = False

    partner_id = fields.Many2one(comodel_name="res.partner", string="Contacto", required=True, ondelete="cascade", index=True)
    name = fields.Char(string="Nombre", required=True)
    rel_docs = fields.One2many(comodel_name="ir.attachment", inverse_name="documento_id", string="Documentos")
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    expiration_date = fields.Date(string="Fecha de caducidad")
    valid = fields.Boolean(compute=_get_valido, string="Documento vigente")

    def unlink(self):
        # rel_docs (ir.attachment) no tiene ondelete='cascade' hacia aquí: si no lo
        # borramos a mano, el archivo se queda huérfano en la base de datos al borrar
        # la fila desde la pestaña "Documentos".
        self.rel_docs.unlink()
        return super().unlink()

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}

    def add_docs(self):
        self.ensure_one()
        view = self.env.ref('leulit.leulit_documento_adjuntar_form', raise_if_not_found=False)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Añadir Documento',
            'res_model': 'leulit.documento',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'res_id': self.id,
            'flags': {'form': {'action_buttons': True}}
        }

    def _migrar_adjuntos_sueltos(self, model_name, hoy):
        """
        Rescata, para cada registro de model_name, los ir.attachment sueltos
        colgados de él (típicamente subidos por el clip del chatter, sin
        fecha de caducidad ni metadatos) y crea un leulit.documento por cada
        uno, usando record.partner_id (el registro debe tenerlo, directo o
        _inherits). Devuelve cuántos ha migrado.
        """
        migrados = 0
        for record in self.env[model_name].search([]):
            if not record.partner_id:
                continue
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', model_name),
                ('res_id', '=', record.id),
                ('documento_id', '=', False),
            ])
            for attachment in attachments:
                doc = self.create({
                    'partner_id': record.partner_id.id,
                    'name': attachment.name or 'Documento',
                    'date': attachment.create_date.date() if attachment.create_date else hoy,
                })
                attachment.write({'documento_id': doc.id})
                migrados += 1
        return migrados

    def migrar_documentos_legacy(self):
        """
        Migración manual, bajo demanda, de los adjuntos sueltos del clip del
        chatter (alumno, mecánico, trabajador de calidad, personal CAMO,
        empleado) al modelo unificado leulit.documento.

        Los mecanismos antiguos de alumno (SENASA) y piloto (piloto_adjunto)
        ya se eliminaron una vez migrados sus datos; este método ya no los
        toca.

        Se lanza a mano desde el botón del asistente "Migrar documentos
        antiguos" (menú Ajustes, solo administradores), nunca
        automáticamente al actualizar un módulo. Es segura de ejecutar más
        de una vez: un adjunto que ya tiene documento_id asignado no se
        vuelve a migrar.

        Cada bloque comprueba si el modelo de origen existe antes de tocarlo,
        para no reventar si algún día se desinstala leulit_escuela/
        leulit_taller/leulit_calidad/leulit_camo.

        Devuelve una lista de líneas de texto con el resumen de lo migrado.
        """
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Solo un administrador puede ejecutar esta migración."))

        resumen = []
        hoy = fields.Date.context_today(self)

        # Adjuntos sueltos colgados directamente de leulit.alumno (chatter)
        if 'leulit.alumno' in self.env:
            migrados = self._migrar_adjuntos_sueltos('leulit.alumno', hoy)
            resumen.append('%s adjuntos sueltos de alumno' % migrados)

        # Adjuntos de chatter colgados de leulit.mecanico
        if 'leulit.mecanico' in self.env:
            migrados = self._migrar_adjuntos_sueltos('leulit.mecanico', hoy)
            resumen.append('%s adjuntos de chatter de mecánico' % migrados)

        # Adjuntos de chatter colgados de leulit.calidad_worker
        if 'leulit.calidad_worker' in self.env:
            migrados = self._migrar_adjuntos_sueltos('leulit.calidad_worker', hoy)
            resumen.append('%s adjuntos de chatter de trabajador de calidad' % migrados)

        # Adjuntos de chatter colgados de leulit.camo_worker
        if 'leulit.camo_worker' in self.env:
            migrados = self._migrar_adjuntos_sueltos('leulit.camo_worker', hoy)
            resumen.append('%s adjuntos de chatter de personal CAMO' % migrados)

        # Adjuntos de chatter colgados directamente de hr.employee. A diferencia de
        # los anteriores, hr.employee no tiene partner_id propio (no es _inherits de
        # res.partner): hay que resolver el contacto vía user_id.partner_id. Un empleado
        # sin usuario de login no tiene dónde migrar sus adjuntos y se omite.
        if 'hr.employee' in self.env:
            migrados = 0
            for employee in self.env['hr.employee'].search([]):
                if not employee.user_id or not employee.user_id.partner_id:
                    continue
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'hr.employee'),
                    ('res_id', '=', employee.id),
                    ('documento_id', '=', False),
                ])
                for attachment in attachments:
                    doc = self.create({
                        'partner_id': employee.user_id.partner_id.id,
                        'name': attachment.name or 'Documento',
                        'date': attachment.create_date.date() if attachment.create_date else hoy,
                    })
                    attachment.write({'documento_id': doc.id})
                    migrados += 1
            resumen.append('%s adjuntos de chatter de empleado' % migrados)

        _logger.info('Migración manual a leulit.documento (usuario %s): %s', self.env.user.login, ' | '.join(resumen))
        return resumen
