# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, timedelta
import pytz
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"
    _rec_name = "display_name"


    def unlink(self):
        if self.parent_id:
            if not self.env.user.has_group("leulit.RolIT_developer"):
                raise UserError("Para eliminar un equipo contacte con el departamento IT.")
        return super(MaintenanceEquipment, self).unlink()


    def name_get(self):
        return [(record.id, record.display_name) for record in self]


    @api.depends('name','serial_no')
    def _get_display_name(self):
        for item in self:
            if item.serial_no and item.name:
                item.display_name = '%s (%s)' %(item.serial_no, item.name)
            else:
                item.display_name = '%s' %(item.name)


    def get_childs(self):
        return self.search([('parent_id','=',self.id)])
    

    def get_all_childs(self):
        return self.search([('first_parent','=',self.id)])


    def get_all_childs_app(self):
        datos = self._context.get('args',[])
        items = []
        for item in self.search([('first_parent','=',datos['id'])]):
            items.append(item.production_lot)
        _logger.error('items --> %r',items)
        return items
    

    def get_motor(self):
        motor = False
        for child in self.get_childs():
            if child.production_lot:
                if child.production_lot.is_motor:
                    motor = child
                    return motor
        if motor == False:  
            for child in self.get_childs():
                if child.is_motor:
                    motor = child
                    return motor
        return motor


    def _airtime(self):
        for item in self:
            item.airtime = 0.0
            if item.parent_id and item.from_date:
                datos = self.env['leulit.vuelo'].acumulados_between_dates(item.parent_id.helicoptero.id, item.from_date, item.to_date)
                if datos:
                    item.airtime = datos[0][0]

    def _get_tsn(self):
        for item in self:
            item.tsn = 0.0
            if item.airtime:
                item.tsn = item.airtime + item.horas_inicio

    def _get_tso(self):
        for item in self:
            item.tso = 0.0
            if item.fecha_overhaul:
                if item.parent_id and item.from_date:
                    datos = self.env['leulit.vuelo'].acumulados_between_dates(item.parent_id.helicoptero.id, item.fecha_overhaul, item.to_date)
                    item.tso = datos[0][0] + item.tso_inicio

    def _get_tsi(self):
        for item in self:
            item.tsi = 0.0

    def _instalado_actualmente(self):
        for item in self:
            item.instalado_actualmente = False
            if not item.to_date:
                item.instalado_actualmente = True
            else:
                if item.to_date < datetime.now().date():
                    item.instalado_actualmente = False
                else:
                    item.instalado_actualmente = True
        
    def _get_instalado_actualmente(self, operator, value):
        ids = []
        for item in self.search([]):
            if not item.to_date:
                ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]

    def _get_ng(self):
        for item in self:
            item.ng = 0.0
            if item.ng_acumulado:
                item.ng = item.ng_acumulado + item.ng_start

    def _ng_acumulado(self):
        for item in self:
            item.ng_acumulado = 0.0
            if item.parent_id and item.from_date:
                datos = self.env['leulit.vuelo'].acumulados_between_dates(item.parent_id.helicoptero.id, item.from_date, item.to_date)
                if datos:
                    item.ng_acumulado = datos[0][1]

    def _get_nf(self):
        for item in self:
            item.nf = 0.0
            if item.nf_acumulado :
                item.nf = item.nf_acumulado + item.nf_start

    def _nf_acumulado(self):
        for item in self:
            item.nf_acumulado = 0.0
            if item.parent_id and item.from_date:
                datos = self.env['leulit.vuelo'].acumulados_between_dates(item.parent_id.helicoptero.id, item.from_date, item.to_date)
                if datos:
                    item.nf_acumulado = datos[0][2]

    def _hours_remaining(self):
        for item in self:
            item.hours_remaining = 0.0
            if item.o_life_hours and item.airtime:
                item.hours_remaining = item.o_life_hours - (item.tso_inicio + item.airtime)

    def _days_remaining(self):
        for item in self:
            item.days_remaining = 0

    def is_helicoptero_pieza(self):
        for item in self:
            item.helicoptero_pieza = False
            if item.category_id:
                if item.category_id.name == 'Pieza':
                    item.helicoptero_pieza = True

    def _get_tipomotor(self):
        return (
            ('piston','Pistón'),
            ('turbina','Turbina'),
            ('rpas','RPAS'),
            )
    
    @api.onchange('production_lot')
    def onchange_production_lot(self):
        self.effective_date = datetime.now()

    @api.depends('parent_id')
    def _get_first_parent(self):
        for item in self:
            if item.parent_id:
                parent = item.parent_id
                if parent.parent_id:
                    while parent.parent_id.id != False:
                        parent = parent.parent_id
                item.first_parent = parent.id
            else:
                item.first_parent = False


    display_name = fields.Char(compute=_get_display_name, string="Display name")
    helicoptero = fields.Many2one('leulit.helicoptero', 'Helicóptero')
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')
    fecha_overhaul = fields.Date('Fecha overhaul')
    anofabmoto = fields.Date('Año fabricación')
    tsn = fields.Float(compute='_get_tsn',string='TSN',store=False)
    horas_inicio = fields.Float('Horas inicio')
    airtime = fields.Float(compute='_airtime',string='Airtime',store=False)
    tso_inicio = fields.Float("Horas desde overhaul")
    tso = fields.Float(compute='_get_tso',string='TSO')
    tsi = fields.Float(compute='_get_tsi',string='TSI')
    instalado_actualmente = fields.Boolean(compute='_instalado_actualmente',string='Instalado actualmente',store=False, search=_get_instalado_actualmente)
    ng = fields.Float(compute='_get_ng',string='NG')
    ng_acumulado = fields.Float(compute='_ng_acumulado',string='NG acumulado',store=False)
    ng_start = fields.Float('NG inicio')
    tacometro_start = fields.Float('Tacómetro inicio')
    tacometro = fields.Float('Tacómetro acumulado')
    nf = fields.Float(compute='_get_nf',string='NF')
    nf_start = fields.Float('NF inicio')
    nf_acumulado = fields.Float(compute='_nf_acumulado',string='NF acumulado',store=False)
    o_life_hours = fields.Float(string='Horas vida operativa')
    o_life_days = fields.Float(string='Días operativa')
    hours_remaining = fields.Float(compute='_hours_remaining',string='Hours R.')
    days_remaining = fields.Integer(compute='_days_remaining',string='Days R.')
    helicoptero_pieza = fields.Boolean(compute='is_helicoptero_pieza',string='Is helicoptero pieza?',store=False)
    tipomotor = fields.Selection(_get_tipomotor,'Tipo motor')
    marca_motor = fields.Char(string='Marca motor')
    is_motor = fields.Boolean(string="Es motor?")
    modelomotor = fields.Char('Modelo motor')
    sn = fields.Char('Serial Number')
    production_lot = fields.Many2one(comodel_name="stock.lot", string="Nº Serie")
    airtime_helicopter = fields.Float(related="helicoptero.airtime", string="Total Airtime - TSN (hh:mm)")
    effective_date = fields.Datetime('Fecha efectiva', default=fields.Date.context_today, required=True)
    first_parent = fields.Many2one(compute=_get_first_parent ,comodel_name="maintenance.equipment", string="Primer Padre", store=True)
    aviso = fields.Char(string="Aviso")
    external_aircraft = fields.Boolean(string="External Aircraft", help="Indicates if the equipment is an external aircraft, not managed by the maintenance system.")


    def action_change_production_lot(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20231011_1250_form')
        view_id = view_ref and view_ref[1] or False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cambiar pieza',
            'res_model': 'maintenance.equipment',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': self.id,
            'target': 'new'
        }


    def get_tsn_to_date(self, to_date):
        if self.parent_id:
            helicoptero = self.parent_id.helicoptero.id
        else:
            helicoptero = self.helicoptero.id
        if to_date:
            airtime = self.helicoptero.airtimestart
            for vuelo in self.env['leulit.vuelo'].search([('estado','=','cerrado'),('fechallegada','<=',to_date),('helicoptero_id','=',helicoptero)]):
                airtime += vuelo.airtime
            return airtime
        return 0
    

    def preview_child_list(self):
        res = super(MaintenanceEquipment,self).preview_child_list()
        return {
            "name": _("Child equipment of %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "maintenance.equipment",
            "res_id": self.id,
            "view_mode": "list,form",
            "context": {
                **self.env.context,
                "default_parent_id": self.id,
                "parent_id_editable": False,
            },
            "domain": [("first_parent", "=", self.id)],
        }