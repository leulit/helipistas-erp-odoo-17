from odoo import api, models, fields
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class LeulitAirworthinessDirective(models.Model):
    _name = "leulit.airworthiness_directive"
    _rec_name = "full_name"

    @api.depends('limit_h', 'date_effective', 'aircraft')
    def _get_remaining_hours(self):
        for item in self:
            item.remianing_hours = 0
            if item.limit_h > 0:
                horas_voladas = 0
                vuelos = self.env['leulit.vuelo'].search([('helicoptero_id', '=', item.aircraft.id),('fechavuelo', '>=', item.date_effective),('estado','=','cerrado')])
                for vuelo in vuelos:
                    horas_voladas += vuelo.airtime
                item.remianing_hours = round(item.limit_h - horas_voladas,2)

    @api.depends('limit_date')
    def _get_remaining_days(self):
        for item in self:
            item.remianing_days = 0
            if item.limit_date:
                date_now = datetime.now().date()
                item.remianing_days = (item.limit_date - date_now).days

    @api.depends('limit_h', 'tsn_aircraft')
    def _get_limit_tsn(self):
        for item in self:
            item.limit_tsn = item.limit_h + item.tsn_aircraft

    @api.depends('name_easa', 'name_faa')
    def _get_full_name(self):
        for item in self:
            item.full_name = ''
            if item.name_easa:
                item.full_name += 'E-{0}'.format(item.name_easa)
                if item.name_faa:
                    item.full_name += ' / '
            if item.name_faa:
                item.full_name += 'F-{0}'.format(item.name_faa)


    full_name = fields.Char(compute=_get_full_name, string='Titulo', store=True)
    name_easa = fields.Char(string='EASA')
    subject = fields.Char(string='Subject', required=True)
    rev = fields.Char(string='Rev', required=True)
    date = fields.Date(string='Date', required=True)
    apply = fields.Boolean(string="Apply")
    type_component = fields.Selection(selection=[('aeronave','Aeronave'),('motor','Motor')], string="Type component", required=True)
    type_aircraft = fields.Selection(selection=[('cabri_g2','Cabri G2'),('r22','R22'),('r44','R44'),('ec120','EC120')], string="Type Aircraft")
    pieza_id = fields.Many2one(comodel_name="stock.lot", string="S/N")
    recursive = fields.Boolean(string="Recurrent")
    result = fields.Char(string="Result")
    date_applyed = fields.Date(string="Date applyed")
    hours_applyed = fields.Float(string="Hours applyed")
    sb_ids = fields.Many2many("leulit.service_bulletin", "leulit_sb_ad_rel", "sbulletin_id", "adirective_id", string="Service Bulletins")
    state = fields.Selection(selection=[('active','Active'),('superseded','Superseded'),('cancel','Cancel')], string="State", default="active")
    limit_h = fields.Float(string="Limit Hours")
    limit_tsn = fields.Float(compute=_get_limit_tsn, string="Limit Hours")
    limit_date = fields.Date(string="Limit Date")
    date_effective = fields.Date(string="Effective date")
    aircraft = fields.Many2one(comodel_name="leulit.helicoptero", string="Aircraft")
    tsn_aircraft = fields.Float(string="TSN Aircraft")
    remianing_hours = fields.Float(compute=_get_remaining_hours, string="Remaining hours")
    remianing_days = fields.Integer(compute=_get_remaining_days, string="Remaining days")
    

    name_faa = fields.Char(string="FAA")
    superseded_by = fields.Many2one(comodel_name="leulit.airworthiness_directive", string="Superseded by")
    tasks = fields.One2many(comodel_name="project.task", inverse_name="airworthiness_directive_id", string="Tasks", readonly=True)


    def action_create_task_maintenance(self):
        tags = self.env['project.tags'].search([('name', '=', 'Tareas de mantenimiento')])
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20250724_1244_form')
        view_id = view_ref and view_ref[1] or False

        project_id = int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))
        context={
            'default_airworthiness_directive_id': self.id,
            'default_project_id': project_id,
            'default_tag_ids': tags.ids,
            'default_tipo_tarea_taller': 'airworthiness_directive'
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarea Mantenimiento',
            'res_model': 'project.task',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }


    def action_create_task(self):
        tags = self.env['project.tags'].search([('name', '=', 'Tareas usuarios')])
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20250724_1244_form')
        view_id = view_ref and view_ref[1] or False

        company = self.env['res.company'].search([('name','=','Helipistas S.L.')])
        project = self.env['project.project'].search([('name','=','Internal'),('company_id','=',company.id)])
        context={
            'default_airworthiness_directive_id': self.id,
            'default_project_id': project.id,
            'default_tag_ids': tags.ids,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarea Mantenimiento',
            'res_model': 'project.task',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }