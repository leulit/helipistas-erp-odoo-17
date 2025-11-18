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

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create para establecer res_model en el ir.attachment creado.
        Esto es necesario para que las reglas de seguridad funcionen correctamente.
        """
        records = super().create(vals_list)
        for record in records:
            if record.attachment_id:
                record.attachment_id.write({
                    'res_model': 'leulit.maintenance_manual',
                    'res_id': record.id,
                })
        return records

    @api.model
    def fix_existing_attachments(self):
        """
        Método para corregir attachments existentes que no tienen res_model establecido.
        Se puede ejecutar manualmente desde el shell de Odoo:
        env['leulit.maintenance_manual'].fix_existing_attachments()
        """
        manuals = self.search([])
        fixed_count = 0
        for manual in manuals:
            if manual.attachment_id:
                if not manual.attachment_id.res_model or not manual.attachment_id.res_id:
                    manual.attachment_id.write({
                        'res_model': 'leulit.maintenance_manual',
                        'res_id': manual.id,
                    })
                    fixed_count += 1
        
        # Hacer commit explícito de los cambios
        self.env.cr.commit()
        
        _logger.info(f"Fixed {fixed_count} maintenance manual attachments")
        return fixed_count


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
            

    attachment_id = fields.Many2one(comodel_name="ir.attachment", string="Documento", required=True, ondelete='cascade')
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
        """
        Añade un registro al histórico cuando cambia la fecha de check.
        Usa comandos de escritura (0, 0, vals) para crear registros en One2many
        sin necesidad de que el registro principal tenga ID.
        """
        if self.check:
            # Comando (0, 0, vals) crea un nuevo registro en el One2many
            self.historic_check = [(0, 0, {
                'check': self.check,
            })]
