# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class LeulitRelFormOneLot(models.Model):
    _name = "leulit.rel_formone_lot"
    _rec_name = "pieza_id"


    def _get_pieza_default(self):
        if 'pieza' in self.env.context:
            return self.env.context['pieza']
        return False


    form_one = fields.Many2one(comodel_name="leulit.maintenance_form_one", string="Form One")
    item = fields.Integer(string="Item")
    pieza_id = fields.Many2one(comodel_name="stock.lot", string="Pieza", default=_get_pieza_default)
    qty = fields.Integer(string="Qty", default=1)
    move_created = fields.Boolean(string="Movimiento creado", default=False)
    estado = fields.Selection(related="form_one.estado", string="Estado", store=True)


    def do_move_certificate(self):
        if self.form_one and self.pieza_id:
            move_certificate = self.env['stock.move_certificate'].create({
                'name': self.with_context(force_company=2).env['ir.sequence'].next_by_code('stock.move.certificate') or _('Nuevo'),
                'product_id': self.pieza_id.product_id.id,
                'product_uom_id': self.pieza_id.product_id.uom_id.id,
                'lot_id': self.pieza_id.id,
                'qty': self.qty,
                'date_done': self.form_one.fecha,
                'maintenance_request_id': self.form_one.work_order_id.id,
            })
            move_certificate.action_validate()
            self.move_created = True
        else:
            raise ValidationError("No se ha podido crear el movimiento de certificado, falta información")