# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)


class leulitPilotoAdjunto(models.Model):
    _name           = "leulit.piloto_adjunto"
    _description    = "leulit_piloto_adjunto"

    #  Función para ver si es valido el documento, 
    #  mira si la fecha de hoy es mayor o igual a la fecha de caducidad, en el caso de que exista, 
    #  en el caso contrario, siempre será valido.
    @api.depends('expiration_date')
    def _get_valido(self):
        for item in self:
            item.valid = True
            if item.expiration_date:
                if datetime.now().date() >= item.expiration_date:
                    item.valid = False


    name = fields.Char(string="Nombre", required=True)
    piloto_id = fields.Many2one(comodel_name="leulit.piloto", string="Piloto")
    rel_docs = fields.One2many(comodel_name="ir.attachment", inverse_name="piloto_adjunto_id", string="Documentos")
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    expiration_date = fields.Date(string="Fecha de caducidad")
    valid = fields.Boolean(compute=_get_valido,string="Documento vigente")


    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
            
    def add_docs_piloto(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones', 'leulit_20230829_1717_form')
        view_id = view_ref and view_ref[1] or False

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Añadir Documento',
           'res_model'      : 'leulit.piloto_adjunto',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'res_id'         : self.id,
            'flags'         : {'form': {'action_buttons': True}}
        }
