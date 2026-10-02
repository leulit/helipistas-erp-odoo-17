# -*- encoding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Related a hr.employee -> user_id -> partner_id -> documento_ids. Es un related
    # field, no una columna nueva: no requiere -u con --stop.
    #
    # readonly=False es imprescindible: un related es readonly por defecto, y entonces
    # el cliente web no envía las líneas nuevas al guardar y desaparecen sin error.
    # Se pasa por partner_id y no directamente por user_id.documento_ids para que la
    # escritura caiga en res.partner y no en res.users (que solo un administrador
    # puede modificar en usuarios ajenos).
    #
    # Solo funciona para empleados con user_id (usuario de login) asignado. Es el caso
    # normal para el pequeño porcentaje de personal sin ficha de rol (alumno/piloto/
    # operador/mecánico/calidad/camo) que sí usa el ERP; un empleado sin usuario propio
    # no tiene dónde colgar el documento dentro de este esquema (no existe partner_id
    # unívoco sin pasar por un usuario) y la pestaña le aparecerá vacía y no editable.
    documento_ids = fields.One2many(related='user_id.partner_id.documento_ids', readonly=False, string='Documentos')
