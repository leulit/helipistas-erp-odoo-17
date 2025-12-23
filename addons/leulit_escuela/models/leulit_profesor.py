# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class leulit_profesor(models.Model):
    _name = "leulit.profesor"
    _description = "leulit_profesor"
    _inherits = {'res.partner': 'partner_id'}

    @api.model
    def create(self, vals):
        """Override create to ensure partner always has a name"""
        # Si no hay name en vals y no hay partner_id, evitar la creación
        if 'name' not in vals and 'partner_id' not in vals:
            raise ValidationError(_(
                'No se puede crear el profesor sin nombre.\n\n'
                '⚠️ Causa del error:\n'
                'Se está intentando crear un nuevo profesor pero no se ha proporcionado ningún nombre.\n\n'
                '✅ Solución:\n'
                '1. Asegúrese de escribir el nombre completo del profesor antes de guardar\n'
                '2. Si está usando el formulario, complete el campo "Nombre"\n'
                '3. Si aparece un desplegable de selección, elija un profesor existente en lugar de crear uno nuevo\n\n'
                'Si el problema persiste, contacte con el administrador del sistema.'
            ))
        
        # Si hay name pero no partner_id, el _inherits creará el partner automáticamente
        return super(leulit_profesor, self).create(vals)

    @api.model
    def getPartnerId(self):
        return self.partner_id.id


    adjunto = fields.Boolean('Profesor adjunto')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner', required=True, ondelete='cascade')
    profesor_erp = fields.Integer('Profesor ERP')
    partes_escuela = fields.One2many('leulit.parte_escuela', 'profesor', 'Partes Escuela')
    employee = fields.Many2one(related='partner_id.user_ids.employee_id',comodel_name='hr.employee',string='Empleado')
    