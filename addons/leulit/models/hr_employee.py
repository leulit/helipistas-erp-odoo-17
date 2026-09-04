# -*- encoding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # res.users ya expone documento_ids gratis (se _inherits de res.partner), así que
    # solo hace falta un salto: hr.employee -> user_id -> documento_ids. Es un related
    # field, no una columna nueva: no requiere -u con --stop.
    #
    # Solo funciona para empleados con user_id (usuario de login) asignado. Es el caso
    # normal para el pequeño porcentaje de personal sin ficha de rol (alumno/piloto/
    # operador/mecánico/calidad/camo) que sí usa el ERP; un empleado sin usuario propio
    # no tiene dónde colgar el documento dentro de este esquema (no existe partner_id
    # unívoco sin pasar por un usuario) y la pestaña le aparecerá vacía y no editable.
    documento_ids = fields.One2many(related='user_id.documento_ids', string='Documentos')
