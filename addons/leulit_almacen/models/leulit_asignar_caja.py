# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging

_logger = logging.getLogger(__name__)


class LeulitAsignarCaja(models.TransientModel):
    _name = 'leulit.asignar.caja'
    _description = 'Asignar caja a existencias'

    caja_id = fields.Many2one(comodel_name='stock.quant.package', string='Caja')
    estanteria_id = fields.Many2one(related='caja_id.estanteria_id', string='Estantería')
    quant_ids = fields.Many2many(comodel_name='stock.quant', string='Existencias seleccionadas')

    @api.model
    def default_get(self, fields_list):
        res = super(LeulitAsignarCaja, self).default_get(fields_list)
        if self._context.get('active_model') == 'stock.quant':
            res['quant_ids'] = [(6, 0, self._context.get('active_ids', []))]
        return res

    def action_asignar(self):
        self.ensure_one()
        if not self.caja_id:
            raise UserError(_('Indica la caja a la que quieres asignar las piezas.'))
        quants = self.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        if not quants:
            raise UserError(_('Ninguna de las líneas seleccionadas está en una ubicación interna de almacén.'))
        # inventory_mode=False es imprescindible: stock.quant.write() prohíbe escribir package_id
        # cuando el contexto trae inventory_mode (ver _get_forbidden_fields_write en
        # stock/models/stock_quant.py). La pantalla de Inventario físico lo trae puesto.
        quants.sudo().with_context(inventory_mode=False).write({'package_id': self.caja_id.id})
        return {'type': 'ir.actions.act_window_close'}

    def action_quitar(self):
        self.ensure_one()
        quants = self.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        quants.sudo().with_context(inventory_mode=False).write({'package_id': False})
        return {'type': 'ir.actions.act_window_close'}
