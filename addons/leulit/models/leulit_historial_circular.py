# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_historial_circular(models.Model):
    _name = "leulit.historial_circular"
    _description = "leulit_historial_circular"
    

    def unlink(self):
        for item in self:
            if item.circular_id.autor_id.id == self.env.uid:
                return super().unlink()
            else:
                raise UserError('El usuario no esta autorizado a realizar esta modificación')


    @api.depends('partner_id')
    def _get_user(self):
        for item in self:
            if item.partner_id:
                user = self.env['res.users'].search([('partner_id','=',item.partner_id.id)])
                item.user_id = user.id

    
    def write(self, vals):
        for item in self:
            circular = False
            if 'circular_id' in vals:
                circular = self.env['leulit.circular'].browse(vals['circular_id'])
            if item.circular_id:
                circular = item.circular_id
            if circular:
                if circular.autor_id.id == self.env.uid:
                    return super().write(vals)

            if item.user_id.id == self.env.uid:
                if 'recibido' in vals or 'leido' in vals or 'entendido' in vals or 'enviado' in vals:
                    return super().write(vals)
            else:
                raise UserError('El usuario no esta autorizado a realizar esta modificación')

    
    partner_id = fields.Many2one('res.partner','Empleado',domain="[('user_ids','!=',False)]")
    user_id = fields.Many2one(compute=_get_user,comodel_name="res.users",string='Usuario',store=True)
    partner_email = fields.Char(related='partner_id.email',string='E-mail',store=True)
    circular_id = fields.Many2one(comodel_name='leulit.circular',string='Circular',ondelete='cascade')
    recibido = fields.Boolean('Recibido')
    leido = fields.Boolean('Leído')
    entendido = fields.Boolean('Entendido')
    enviado = fields.Boolean('Enviado')