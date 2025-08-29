# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class Calibracion(models.Model):
    _name = "leulit.calibracion"
    _description = "leulit_calibracion"
    _order = "proxima_calibracion desc"


    @api.depends('proxima_calibracion')
    def _calibrado(self):
        for item in self:
            item.calibrado = False
            if item.proxima_calibracion:
                if item.proxima_calibracion > datetime.now().date():
                    item.calibrado = True

        
    def add_docs_calibracion(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_almacen', 'leulit_20230222_1614_form')
        view_id = view_ref and view_ref[1] or False

        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Añadir Documento calibración',
           'res_model'      : 'leulit.calibracion',
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'res_id'         : self.id,
            'flags'         : {'form': {'action_buttons': True}}
        }


    def write(self, vals):
        if 'fecha_calibracion' in vals:
            fecha_proxima = datetime.strptime(vals['fecha_calibracion'], '%Y-%m-%d').date() + relativedelta(months=self.herramienta.frecuencia_meses)
            vals['proxima_calibracion'] = fecha_proxima
        return super(Calibracion, self).write(vals)
    
    @api.model
    def create(self, vals):
        if 'fecha_calibracion' in vals:
            herramienta = self.env['stock.lot'].search([('id','=',vals['herramienta'])])
            fecha_proxima = datetime.strptime(vals['fecha_calibracion'], '%Y-%m-%d').date() + relativedelta(months=herramienta.frecuencia_meses)
            vals['proxima_calibracion'] = fecha_proxima
        return super(Calibracion, self).create(vals)


    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
    

    n_certificado = fields.Char(string="Nº Certificado", required=True)
    fecha_calibracion = fields.Date(string="Fecha calibración", default=fields.Date.context_today)
    herramienta = fields.Many2one(comodel_name="stock.lot", string="Herramienta")
    verificador = fields.Char(string="Verificador", required=True)
    calibrado = fields.Boolean(compute="_calibrado",string="Calibración vigente")
    rel_docs = fields.One2many(comodel_name="ir.attachment", inverse_name="calibracion_id", string="Documentos")
    proxima_calibracion = fields.Date(string="Próxima calibración")
