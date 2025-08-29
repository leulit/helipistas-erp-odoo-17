# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib
import pytz

_logger = logging.getLogger(__name__)


class leulit_checklist(models.Model):
    _name           = "leulit.checklist"
    _inherit        = ["leulit.checklist"]
   
    def check_freelance_pilot(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('leulit_operaciones.leulit_20250320_1123_form')
        view_id = view_ref and view_ref[1] or False
        context = {
            'default_date' : self.fecha_doit,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actividad Aerea',
            'res_model': 'leulit.wizard_freelance_actividad_aerea',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context
        }

    def is_freelance_pilot(self):
        for item in self:
            item.freelance_pilot = False
            if self.env['res.users'].get_piloto_freelance() and len(self.env['leulit.freelance_actividad_aerea'].search([('user','=',self.env.uid),('date','=',item.fecha_doit)])) == 0:
                item.freelance_pilot = True

    def write(self, vals):
        if self.freelance_pilot:
            raise UserError(_("No se puede editar la checklist, primero debes pulsar el boton Certificado 16B."))
        return super(leulit_checklist, self).write(vals)


    timesheet_ids = fields.One2many(comodel_name="account.analytic.line", inverse_name="checklist_id", string="Partes de horas")
    freelance_pilot = fields.Boolean(compute=is_freelance_pilot, string="Usuario piloto freelance")

