# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_event_resource(models.Model):
    _name       = "leulit.event_resource"
    _description = 'Recurso de Evento de Planificación'
    _rec_name   = 'resource'
    _order      = "hora_ini asc"


    def _get_tipos_planificacion(self):
        return utilitylib.leulit_get_tipos_planificacion()

    dummy = fields.Char(string="")
    nodisponible = fields.Boolean(string='No disponible', )
    work_hours = fields.Float(string='H. previstas')
    availability_hours = fields.Float(string='H. disponibilidad')
    resource = fields.Many2one(comodel_name='leulit.resource',string='Recurso') 
    color = fields.Char(related='resource.color',string='Color')
    email = fields.Char(related='resource.email',string='Mail')
    type = fields.Selection(related='resource.type',string='Tipo',store=True)
    rol = fields.Selection([('7', 'Alumno'),('5', 'Instructor de vuelo'),('6', 'Instructor de teóricas'),('1','Máquina'),('3','Operador tierra'),('4','Otros'),('2', 'Piloto'),], '', required=False)
    event = fields.Many2one(comodel_name='calendar.event', string='Evento', ondelete='cascade')
    duration = fields.Float(related='event.duration',string="Duración")
    comentarios = fields.Html(related='event.description',string='Comentarios')
    asunto = fields.Char(related='event.name',string='Tema')
    cancelado = fields.Boolean(related='event.cancelado', string='Cancelado')
    type_event = fields.Many2one(related='event.type_event', comodel_name='leulit.tipo_planificacion', string='Tipo')
    tipo = fields.Selection(related='event.tipo',selection=_get_tipos_planificacion,string='Tipo')
    fecha_ini = fields.Date(string='Fecha Inicial')
    fecha_fin = fields.Date(string='Fecha Final')
    hora_ini = fields.Float(string='Hora inicio')
    hora_fin = fields.Float(string='Hora fin')
    date = fields.Datetime(string='Fecha')
    date_deadline = fields.Datetime(string='Fecha')
    reunion = fields.Many2one(comodel_name='leulit.reunion', string='Reunion')
    byday_id = fields.Many2one(comodel_name="leulit.event.resource.byday", string="Byday")

    @api.constrains("work_hours")
    def _check_work_hours(self):
        for item in self:
            if item.resource.aeronave:
                if not item.work_hours > 0:
                    raise ValidationError("Se debe indicar H.V. en los recursos.")
