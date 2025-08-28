from odoo import api, models, fields
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class LeulitServiceBulletin(models.Model):
    _name = "leulit.service_bulletin"

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

    name = fields.Char(string='SB', required=True)
    subject = fields.Char(string='Subject', required=True)
    rev = fields.Char(string='Rev', required=True)
    date = fields.Date(string='Date', required=True)
    apply = fields.Boolean(string="Apply")
    type_sb = fields.Selection(selection=[('mandatory', 'Mandatory'), ('recommended', 'Recommended'),('optional','Optional'),('repair','Repair')], string="Type")
    type_component = fields.Selection(selection=[('aeronave','Aeronave'),('motor','Motor')], string="Type component", required=True)
    type_aircraft = fields.Selection(selection=[('cabri_g2','Cabri G2'),('r22','R22'),('r44','R44'),('ec120','EC120')], string="Type Aircraft")
    pieza_id = fields.Many2one(comodel_name="stock.lot", string="S/N")
    recursive = fields.Boolean(string="Recurrent")
    result = fields.Char(string="Result")
    date_applyed = fields.Date(string="Date applied")
    hours_applyed = fields.Float(string="Hours applied")
    ad_ids = fields.Many2many("leulit.airworthiness_directive", "leulit_sb_ad_rel", "adirective_id", "sbulletin_id", string="Airworthiness Directives")
    state = fields.Selection(selection=[('active','Active'),('cancel','Cancel')], string="State", default="active")
    limit_h = fields.Float(string="Limit Hours")
    limit_tsn = fields.Float(compute=_get_limit_tsn, string="Limit Hours")
    limit_date = fields.Date(string="Limit Date")
    date_effective = fields.Date(string="Effective date")
    aircraft = fields.Many2one(comodel_name="leulit.helicoptero", string="Aircraft")
    tsn_aircraft = fields.Float(string="TSN Aircraft")
    remianing_hours = fields.Float(compute=_get_remaining_hours, string="Remaining hours")
    remianing_days = fields.Integer(compute=_get_remaining_days, string="Remaining days")
    