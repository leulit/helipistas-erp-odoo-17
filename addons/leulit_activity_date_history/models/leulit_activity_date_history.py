# -*- encoding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class LeulitActivityDateHistory(models.Model):
    _name = 'leulit.activity.date.history'
    _description = 'Histórico de cambios de fecha de vencimiento de actividad'
    _order = 'fecha_cambio desc'

    activity_id = fields.Many2one(
        comodel_name='mail.activity',
        string='Actividad',
        required=True,
        ondelete='cascade'
    )
    activity_type_id = fields.Many2one(
        related='activity_id.activity_type_id',
        string='Tipo de actividad',
        store=True
    )
    res_model = fields.Char(
        related='activity_id.res_model',
        string='Modelo',
        store=True
    )
    res_name = fields.Char(
        related='activity_id.res_name',
        string='Registro',
        store=True
    )
    fecha_anterior = fields.Date(string='Fecha anterior', required=True)
    fecha_nueva = fields.Date(string='Fecha nueva', required=True)
    fecha_cambio = fields.Datetime(
        string='Fecha del cambio',
        required=True,
        default=fields.Datetime.now
    )
    usuario_id = fields.Many2one(
        comodel_name='res.users',
        string='Modificado por',
        required=True,
        default=lambda self: self.env.uid,
        ondelete='restrict'
    )
    nota = fields.Text(string='Nota')
