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

    def migrar_documentos_legacy(self):
        """
        Migración manual, bajo demanda, de los mecanismos de documentación
        antiguos (SENASA/adjuntos de alumno, piloto_adjunto de piloto,
        adjuntos de chatter de mecánico) al modelo unificado leulit.documento.

        Se lanza a mano desde el botón del asistente "Migrar documentos
        antiguos" (menú Gestión Documental, solo administradores), nunca
        automáticamente al actualizar un módulo. Es segura de ejecutar más
        de una vez: un adjunto que ya tiene documento_id asignado no se
        vuelve a migrar (la única excepción son las filas SENASA/piloto sin
        ningún adjunto vinculado nunca, donde se comprueba por
        partner_id+nombre+fecha en vez de por adjunto).

        Cada bloque comprueba si el modelo de origen existe antes de tocarlo,
        para no reventar si algún día se desinstala leulit_escuela/
        leulit_operaciones/leulit_taller.

        Devuelve una lista de líneas de texto con el resumen de lo migrado.
        """
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Solo un administrador puede ejecutar esta migración."))

        resumen = []
        hoy = fields.Date.context_today(self)

        # 1) SENASA: leulit.rel_alumno_documentacion -> leulit.documento
        if 'leulit.rel_alumno_documentacion' in self.env:
            migrados = 0
            for rel in self.env['leulit.rel_alumno_documentacion'].search([]):
                if not rel.alumno_id or not rel.alumno_id.partner_id:
                    continue
                nombre = rel.name or 'Documento SENASA'
                fecha = rel.fecha_expedicion or hoy
                pendientes = rel.doc_alumno.filtered(lambda a: not a.documento_id)
                if rel.doc_alumno:
                    if not pendientes:
                        continue  # todos sus adjuntos ya migrados
                else:
                    ya_existe = self.search_count([
                        ('partner_id', '=', rel.alumno_id.partner_id.id),
                        ('name', '=', nombre),
                        ('date', '=', fecha),
                    ])
                    if ya_existe:
                        continue
                doc = self.create({
                    'partner_id': rel.alumno_id.partner_id.id,
                    'name': nombre,
                    'date': fecha,
                    'expiration_date': rel.fecha_validez or False,
                })
                if pendientes:
                    pendientes.write({'documento_id': doc.id})
                migrados += 1
            resumen.append('%s documentos SENASA (alumno)' % migrados)

        # 2) Adjuntos sueltos colgados directamente de leulit.alumno (chatter)
        if 'leulit.alumno' in self.env:
            migrados = 0
            for alumno in self.env['leulit.alumno'].search([]):
                if not alumno.partner_id:
                    continue
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'leulit.alumno'),
                    ('res_id', '=', alumno.id),
                    ('documento_id', '=', False),
                ])
                for attachment in attachments:
                    doc = self.create({
                        'partner_id': alumno.partner_id.id,
                        'name': attachment.name or 'Documento',
                        'date': attachment.create_date.date() if attachment.create_date else hoy,
                    })
                    attachment.write({'documento_id': doc.id})
                    migrados += 1
            resumen.append('%s adjuntos sueltos de alumno' % migrados)

        # 3) leulit.piloto_adjunto -> leulit.documento
        if 'leulit.piloto_adjunto' in self.env:
            migrados = 0
            for adjunto in self.env['leulit.piloto_adjunto'].search([]):
                if not adjunto.piloto_id or not adjunto.piloto_id.partner_id:
                    continue
                nombre = adjunto.name or 'Documento'
                fecha = adjunto.date or hoy
                pendientes = adjunto.rel_docs.filtered(lambda a: not a.documento_id)
                if adjunto.rel_docs:
                    if not pendientes:
                        continue
                else:
                    ya_existe = self.search_count([
                        ('partner_id', '=', adjunto.piloto_id.partner_id.id),
                        ('name', '=', nombre),
                        ('date', '=', fecha),
                    ])
                    if ya_existe:
                        continue
                doc = self.create({
                    'partner_id': adjunto.piloto_id.partner_id.id,
                    'name': nombre,
                    'date': fecha,
                    'expiration_date': adjunto.expiration_date or False,
                })
                if pendientes:
                    pendientes.write({'documento_id': doc.id})
                migrados += 1
            resumen.append('%s documentos de piloto' % migrados)

        # 4) Adjuntos de chatter colgados de leulit.mecanico
        if 'leulit.mecanico' in self.env:
            migrados = 0
            for mecanico in self.env['leulit.mecanico'].search([]):
                if not mecanico.partner_id:
                    continue
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'leulit.mecanico'),
                    ('res_id', '=', mecanico.id),
                    ('documento_id', '=', False),
                ])
                for attachment in attachments:
                    doc = self.create({
                        'partner_id': mecanico.partner_id.id,
                        'name': attachment.name or 'Documento',
                        'date': attachment.create_date.date() if attachment.create_date else hoy,
                    })
                    attachment.write({'documento_id': doc.id})
                    migrados += 1
            resumen.append('%s adjuntos de chatter de mecánico' % migrados)

        _logger.info('Migración manual a leulit.documento (usuario %s): %s', self.env.user.login, ' | '.join(resumen))
        return resumen
