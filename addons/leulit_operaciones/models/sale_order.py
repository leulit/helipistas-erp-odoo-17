# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class sale_order(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    def _get_tipos(self):
        return utilitylib.leulit_get_tipos_helicopteros()

    def _compute_display_name(self):
        super()._compute_display_name()
        for order in self:
            name = order.name
            if order.partner_id.name:
                name = '%s - %s' % (name, order.partner_id.complete_name)
            if order.origin:
                name = '%s [%s]' % (name, order.origin)
            order.display_name = name

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
        """Sobrescribir búsqueda para incluir búsqueda por nombre del cliente"""
        domain = domain or []
        if name:
            # Buscar por número de presupuesto, nombre del cliente u origen
            domain = ['|', '|', 
                ('name', operator, name),
                ('partner_id.name', operator, name),
                ('origin', operator, name)
            ] + domain
        return self._search(domain, limit=limit, order=order)
    
    @api.depends('invoice_status')
    def _get_is_flight_part(self):
        for item in self:
            flag = True
            if item.invoice_status != 'invoiced':
                flag = False
            item.flag_flight_part = flag

    def search_is_flight_part(self, operator, value):
        ids = []
        for item in self.search([]):
            if value == True and operator == '=':
                if len(item.invoice_ids) == 0:
                    ids.append(item.id)
                else: 
                    if item.invoice_status != 'invoiced':
                        ids.append(item.id)
        return [('id', 'in', ids)]
    
    
    vuelos = fields.One2many(comodel_name='leulit.vuelo', inverse_name='presupuesto_vuelo', string='Vuelos')
    flag_flight_part = fields.Boolean(compute=_get_is_flight_part, search=search_is_flight_part, string="")
    tipo_aeronave = fields.Selection(selection=_get_tipos, string="Tipo de Aeronave")
    tipo_operativo = fields.Char(string="Tipo de Operativo")
    fecha_servicio = fields.Date(string="Fecha del Servicio")
    tiempo_servicio = fields.Float(string="Tiempo Presupuestado")
    pasajeros = fields.Char(string="Pasajeros a Bordo")
    ruta_detallada = fields.Html(string="Ruta Detallada", default="<b style='font-size: 14px;'>Lugar y hora de salida:</b><br/><b style='font-size: 14px;'>Lugar y hora de llegada:</b><br/><b style='font-size: 14px;'>Lugar y hora de salida:</b><br/><b style='font-size: 14px;'>Lugar y hora de llegada:</b>")
    ruta_servicio = fields.Html(string="Ruta", default="<b style='font-size: 14px;'>Ruta de vuelo:</b>")
    aumento_presupuesto = fields.Boolean(string="Aumento del Presupuesto en vuelo")
    desarrollo_servicio = fields.Html(string="Desarrollo del Servicio", default="<b style='font-size: 14px;'>Desarrollo del servicio:</b>")
    personal_equipamiento = fields.Html(string="Personal y Equipamiento para el Servicio", default="<b style='font-size: 14px;'>Personal operador de la compañía:</b><br/><b style='font-size: 14px;'>Vehículo terrestre:</b><br/><b style='font-size: 14px;'>Tipo de operador:</b>")

