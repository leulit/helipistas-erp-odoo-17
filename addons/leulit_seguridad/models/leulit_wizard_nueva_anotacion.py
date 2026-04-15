# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

TEMPLATES_ANOTACION = {
    'flotadores': (
        "Installation of emergency floatation gear on aircraft {helicoptero}.\n"
        "Work carried out in accordance with the applicable Maintenance Manual.\n"
        "Aircraft released to service."
    ),
}


class leulit_wizard_nueva_anotacion(models.TransientModel):
    _name        = "leulit.wizard_nueva_anotacion"
    _description = "leulit_wizard_nueva_anotacion"

    helicoptero_id = fields.Many2one(
        'leulit.helicoptero', 'Helicopter',
        required=True, domain="[('baja','=',False)]"
    )
    fecha = fields.Date('Date', required=True, default=fields.Date.today)
    tipo_anotacion = fields.Selection([
        ('flotadores', 'Instalación de flotadores'),
    ], string='Annotation type', required=True)
    anotacion = fields.Text('Annotation')
    rol_informa = fields.Selection([('1','Pilot'),('2','Mechanic'),('3','CAMO'),('4','Others')],'Who')

    @api.onchange('tipo_anotacion', 'helicoptero_id')
    def _onchange_tipo_anotacion(self):
        if not self.tipo_anotacion:
            return
        template = TEMPLATES_ANOTACION.get(self.tipo_anotacion, '')
        helicoptero_name = self.helicoptero_id.name if self.helicoptero_id else '___'
        self.anotacion = template.format(helicoptero=helicoptero_name)

    def action_crear_anotacion(self):
        if not self.anotacion:
            raise UserError(_('La anotación no puede estar vacía.'))
        anotacion = self.env['leulit.anotacion_technical_log'].create({
            'helicoptero_id': self.helicoptero_id.id,
            'fecha': self.fecha,
            'anotacion': self.anotacion,
            'place': 'LEUL',
            'rol_informa': self.rol_informa,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'leulit.anotacion_technical_log',
            'view_mode': 'form',
            'res_id': anotacion.id,
            'target': 'current',
        }
