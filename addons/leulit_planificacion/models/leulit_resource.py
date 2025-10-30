# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_resource(models.Model):
    _name = 'leulit.resource'
    _order = 'name asc'


    def _get_work_time(self):
        objpool = self.env['leulit.event_resource']
        for item in self:
            event_resources = objpool.search([('resource','=',item.id)])
            valor = 0
            for event_resource_item in event_resources:
                valor = valor + event_resource_item.work_hours
            item.work_time = valor


    def _get_availability_time(self):
        objpool = self.env['leulit.event_resource']
        for item in self:
            event_resources = objpool.search([('resource','=',item.id)])
            valor = 0
            for event_resource_item in event_resources:
                valor = valor + event_resource_item.availability_hours
            item.availability_time = valor

    @api.onchange('aeronave')
    def onchange_maquina(self):
        if self.aeronave:
            self.name = self.aeronave.name
            self.user = False


    @api.onchange('user')
    def onchange_user(self):
        if self.user:
            self.name = self.user.name
            self.aeronave = False

    @api.depends('partner')
    def _get_piloto(self):
        for item in self:
            valor = None
            if item.partner:
                piloto = self.env['leulit.piloto'].search([('partner_id','=',item.partner.id)])
                if piloto and piloto.id:
                    valor = piloto.id
            item.piloto = valor
    
    @api.depends('partner')
    def _get_alumno(self):
        for item in self:
            valor = None
            if item.partner:
                alumno = self.env['leulit.alumno'].search([('partner_id','=',item.partner.id)])
                if alumno and alumno.id:
                    valor = alumno.id
            item.piloto = valor

    @api.depends('user')
    def _get_partner(self):
        for item in self:
            valor = None
            if item.user:
                if item.user.partner_id:
                    valor = item.user.partner_id.id
            item.partner = valor


    name = fields.Char('Nombre', )
    event_resource = fields.One2many('leulit.event_resource', 'resource', 'Recurso')
    type = fields.Selection([('persona', 'Empleado'), ('maquina', 'Máquina'), ('alumno','Alumno')], 'Tipo recurso')
    work_time = fields.Float(compute=_get_work_time,string='Tiempo de trabajo')
    availability_time = fields.Float(compute=_get_availability_time,string='Tiempo de disponibilidad')
    user = fields.Many2one('res.users','Usuario')
    partner = fields.Many2one(compute=_get_partner,comodel_name='res.partner',string='Contacto',store=False)
    email = fields.Char(related='partner.email',string='Mail',store=False)
    active = fields.Boolean(string='Estado')
    color = fields.Char('Color')
    piloto = fields.Many2one(compute=_get_piloto,comodel_name='leulit.piloto',string='Piloto',store=False)
    alumno = fields.Many2one(compute=_get_alumno,comodel_name='leulit.alumno',string='Alumno',store=False)
    aeronave = fields.Many2one('leulit.helicoptero','Nombre')
    strhoras_remanente = fields.Char(related='aeronave.strhoras_remanente',string='Horas vuelo restantes')