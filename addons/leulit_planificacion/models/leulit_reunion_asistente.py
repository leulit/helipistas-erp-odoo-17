# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_reunion_asistente(models.Model):
    _name = "leulit.reunion_asistente"
    _description = "leulit_reunion_asistente"
    

    def write(self, values):
        for item in self:
            if item.user_id and self.env.uid == item.user_id.id:
                super(leulit_reunion_asistente,self).write(values)
            else:
                raise UserError('El usuario no esta autorizado a realizar esta modificación')
        return True

    @api.depends('partner_id')
    def _get_user(self):
        for item in self:
            if item.partner_id:
                user = self.env['res.users'].search([('partner_id','=',item.partner_id.id)])
                item.user_id = user.id

    partner_id = fields.Many2one(comodel_name='res.partner',string='Empleado', domain="[('user_ids','!=',False)]")
    user_id = fields.Many2one(compute=_get_user,comodel_name='res.users',string='Usuario',store=True)
    reunion_id = fields.Many2one(comodel_name='leulit.reunion',string='Reunión',ondelete='cascade')
    asistencia = fields.Boolean(string='Asistencia')