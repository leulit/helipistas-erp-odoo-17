# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulitMaintenanceManual(models.Model):
    _name           = "leulit.maintenance_manual"
    _description    = "leulit_maintenance_manual"
    _inherits       = {'ir.attachment': 'attachment_id'}
    _rec_name       = "name"


    def modificar_manual(self):
        for item in self:
            modificacion = item.copy()
            item.active = False
            return {
                'name': "Modificar Manual",
                'type': 'ir.actions.act_window',
                'res_model': 'leulit.maintenance_manual',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': modificacion.id,
                'target': 'new',
            }
            

    attachment_id = fields.Many2one(comodel_name="ir.attachment", string="Documento")
    categoria_id = fields.Many2one(comodel_name="leulit.categoria_manual", string="Categoria")
    descripcion = fields.Char(string="Descripción")
    pn = fields.Char(string="P/N")
    rev_n = fields.Char(string="Rev. No")
    rev = fields.Date(string="Rev. Date")
    caducidad = fields.Date(string="Caducidad suscripción")
    task_id = fields.Many2one(comodel_name="leulit.maintenance_manual", string="Tarea")
    check = fields.Date(string="Check")
    historic_check = fields.One2many(comodel_name="leulit.maintenance_manual_check", inverse_name="maintenance_manual_id", string="Histórico Check")
    link_web = fields.Char(string="Enlace")
    active = fields.Boolean(string="Activo", default=True)


    @api.onchange('check')
    def onchange_check(self):
        self.env['leulit.maintenance_manual_check'].create({
            'check':self.check,
            'maintenance_manual_id': self.id
        })
