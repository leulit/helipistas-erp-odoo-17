# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_recurso_disponibilidad(models.Model):
    _name = "leulit.recurso_disponibilidad"
    _description = "leulit_recurso_disponibilidad"

    @api.onchange('fecha_disp')
    def onchange_fecha_disponibilidad(self):
        ids_resources = []
        if self.fecha_disp:
            ids_result_ocup = self.env['leulit.event_resource'].search([('fecha_ini', '=', self.fecha_disp)])
            for ocup in ids_result_ocup:
                ids_resources.append(ocup.resource.id)
            ids_result_disp = self.env['leulit.resource'].search([('id', 'not in', ids_resources),('active','=',True)])
        
            self.resource_fields_ocupados = ids_result_ocup.ids if ids_result_ocup else False
            self.resource_fields_disponibles = ids_result_disp.ids if ids_result_disp else False



    fecha_disp = fields.Date('Fecha Disponibilidad')
    resource_fields_ocupados = fields.Many2many('leulit.event_resource', 'rel_disp_event_ocup', 'disp_id', 'event_id', 'Recurso Ocupados')
    resource_fields_disponibles = fields.Many2many('leulit.resource', 'rel_disp_event_disp', 'disp_id', 'resource_id', 'Recursos Disponibles')