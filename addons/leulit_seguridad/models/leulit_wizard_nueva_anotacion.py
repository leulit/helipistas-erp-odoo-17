# -*- encoding: utf-8 -*-

from datetime import datetime
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class leulit_wizard_nueva_anotacion(models.TransientModel):
    _name = "leulit.wizard_nueva_anotacion"
    _description = "leulit_wizard_nueva_anotacion"

    helicoptero_id = fields.Many2one(
        'leulit.helicoptero', 'Helicopter',
        required=True, domain="[('baja','=',False)]"
    )
    fecha = fields.Date('Date', required=True, default=fields.Date.today)
    rol_informa = fields.Selection(
        [('1', 'Pilot'), ('2', 'Mechanic'), ('3', 'CAMO'), ('4', 'Others')],
        'Who', required=True
    )
    vuelo_id = fields.Many2one('leulit.vuelo', 'Flight')
    hora_limite = fields.Char('Deadline time (HH:MM)', default='12:00')

    instalar_dual_control = fields.Boolean('Dual control')
    instalar_cargo_hook_mirror = fields.Boolean('Cargo hook and mirror')
    instalar_floats = fields.Boolean('Floats')
    instalar_life_raft = fields.Boolean('Life raft')
    instalar_life_vests_qty = fields.Integer('Life vests qty')
    instalar_headsets_qty = fields.Integer('Headsets qty')
    instalar_tyler = fields.Boolean('Tyler', help="Tyler universal mount for attaching cameras to the R44/R44II — left side.")
    instalar_gss = fields.Boolean('GSS', help="Gyro-Stabilized Systems. ZatzWorks R44M-001 Utility Camera Mount — forward mount, for attaching cameras to the R44/R44II - right side.")
    instalar_cineflex = fields.Boolean('Cineflex')
    instalar_lidar_system = fields.Boolean('Lidar system')
    instalar_af120 = fields.Boolean('AF120', help="Air Film Camera Systems AF120 Left Side Universal Camera Mount for EC120B.")

    remover_dual_control = fields.Boolean('Dual control')
    remover_cargo_hook_mirror = fields.Boolean('Cargo hook and mirror')
    remover_floats = fields.Boolean('Floats')
    remover_life_raft = fields.Boolean('Life raft')
    remover_life_vests_qty = fields.Integer('Life vests qty')
    remover_headsets_qty = fields.Integer('Headsets qty')
    remover_tyler = fields.Boolean('Tyler', help="Tyler universal mount for attaching cameras to the R44/R44II — left side.")
    remover_gss = fields.Boolean('GSS', help="Gyro-Stabilized Systems. ZatzWorks R44M-001 Utility Camera Mount — forward mount, for attaching cameras to the R44/R44II - right side.")
    remover_cineflex = fields.Boolean('Cineflex')
    remover_lidar_system = fields.Boolean('Lidar system')
    remover_af120 = fields.Boolean('AF120', help="Air Film Camera Systems AF120 Left Side Universal Camera Mount for EC120B.")

    anotacion = fields.Text('Annotation')
    calendar_event_id = fields.Many2one(comodel_name="calendar.event", string="Evento planificación")

    def _get_selected_items(self, mode):
        items = []
        if mode == 'install':
            if self.instalar_floats:
                items.append('floats')
            if self.instalar_dual_control:
                items.append('dual control')
            if self.instalar_cargo_hook_mirror:
                items.append('cargo hook and mirror')
            if self.instalar_life_raft:
                items.append('life raft')
            if self.instalar_life_vests_qty > 0:
                items.append('{0} life vests'.format(self.instalar_life_vests_qty))
            if self.instalar_headsets_qty > 0:
                items.append('{0} headsets'.format(self.instalar_headsets_qty))
            if self.instalar_tyler:
                items.append('Tyler')
            if self.instalar_gss:
                items.append('GSS')
            if self.instalar_cineflex:
                items.append('Cineflex')
            if self.instalar_lidar_system:
                items.append('Lidar system')
            if self.instalar_af120:
                items.append('AF120')

        if mode == 'remove':
            if self.remover_floats:
                items.append('floats')
            if self.remover_dual_control:
                items.append('dual control')
            if self.remover_cargo_hook_mirror:
                items.append('cargo hook and mirror')
            if self.remover_life_raft:
                items.append('life raft')
            if self.remover_life_vests_qty > 0:
                items.append('{0} life vests'.format(self.remover_life_vests_qty))
            if self.remover_headsets_qty > 0:
                items.append('{0} headsets'.format(self.remover_headsets_qty))
            if self.remover_tyler:
                items.append('Tyler')
            if self.remover_gss:
                items.append('GSS')
            if self.remover_cineflex:
                items.append('Cineflex')
            if self.remover_lidar_system:
                items.append('Lidar system')
            if self.remover_af120:
                items.append('AF120')
        return items

    def _validate_hora(self):
        if not self.hora_limite:
            return False
        try:
            datetime.strptime(self.hora_limite, '%H:%M')
            return True
        except (ValueError, TypeError):
            return False

    def _build_operational_annotation(self):
        install_items = self._get_selected_items('install')
        remove_items = self._get_selected_items('remove')
        fecha_str = self.fecha.strftime('%d/%m/%Y') if self.fecha else 'DD/MM/AAAA'
        hora_str = self.hora_limite if self.hora_limite else 'HH:MM'

        clauses = []
        if install_items:
            clauses.append('{0} must be installed'.format(' / '.join(install_items)))
        if remove_items:
            clauses.append('{0} must be removed'.format(' / '.join(remove_items)))

        if self.vuelo_id and self.vuelo_id.codigo:
            reference_clause = 'before flight to {0}.'.format(self.vuelo_id.codigo)
        else:
            reference_clause = 'before day {0} at {1}.'.format(fecha_str, hora_str)

        if not clauses:
            return (
                'For operational reasons, floats / dual control / cargo hook and mirror / life raft / X life vests / X headsets must be installed, '
                'and floats / dual control / cargo hook and mirror / life raft / X life vests / X headsets must be removed, '
                '{0}'
            ).format(reference_clause)

        actions = ', and '.join(clauses)
        return (
            'For operational reasons, {0}, {1}'
        ).format(actions, reference_clause)

    @api.onchange(
        'helicoptero_id', 'fecha', 'vuelo_id', 'hora_limite',
        'instalar_floats', 'instalar_dual_control', 'instalar_cargo_hook_mirror', 'instalar_life_raft',
        'instalar_life_vests_qty', 'instalar_headsets_qty',
        'instalar_tyler', 'instalar_gss', 'instalar_cineflex', 'instalar_lidar_system', 'instalar_af120',
        'remover_floats', 'remover_dual_control', 'remover_cargo_hook_mirror', 'remover_life_raft',
        'remover_life_vests_qty', 'remover_headsets_qty',
        'remover_tyler', 'remover_gss', 'remover_cineflex', 'remover_lidar_system', 'remover_af120',
    )
    def _onchange_anotacion_operacional(self):
        self.anotacion = self._build_operational_annotation()

    def action_crear_anotacion(self):
        if not self.vuelo_id and (not self.hora_limite or not self._validate_hora()):
            raise UserError(_('Si no indicas vuelo, la hora límite debe tener formato HH:MM.'))
        if not self._get_selected_items('install') and not self._get_selected_items('remove'):
            raise UserError(_('Debes seleccionar al menos un elemento para instalar o remover.'))

        self.anotacion = self._build_operational_annotation()
        if not self.anotacion:
            raise UserError(_('La anotación no puede estar vacía.'))

        anotacion = self.env['leulit.anotacion_technical_log'].create({
            'helicoptero_id': self.helicoptero_id.id,
            'fecha': self.fecha,
            'anotacion': self.anotacion,
            'lugar': 'LEUL',
            'rol_informa': self.rol_informa,
            'calendar_event_id': self.calendar_event_id.id if self.calendar_event_id else False,
            'is_operational': True,
            'flight_id': self.vuelo_id.id if self.vuelo_id else False,
            'deadline_time': self.hora_limite,
            'install_dual_control': self.instalar_dual_control,
            'install_cargo_hook_mirror': self.instalar_cargo_hook_mirror,
            'install_floats': self.instalar_floats,
            'install_life_raft': self.instalar_life_raft,
            'install_life_vests_qty': self.instalar_life_vests_qty,
            'install_headsets_qty': self.instalar_headsets_qty,
            'install_tyler': self.instalar_tyler,
            'install_gss': self.instalar_gss,
            'install_cineflex': self.instalar_cineflex,
            'install_lidar_system': self.instalar_lidar_system,
            'install_af120': self.instalar_af120,
            'remove_dual_control': self.remover_dual_control,
            'remove_cargo_hook_mirror': self.remover_cargo_hook_mirror,
            'remove_floats': self.remover_floats,
            'remove_life_raft': self.remover_life_raft,
            'remove_life_vests_qty': self.remover_life_vests_qty,
            'remove_headsets_qty': self.remover_headsets_qty,
            'remove_tyler': self.remover_tyler,
            'remove_gss': self.remover_gss,
            'remove_cineflex': self.remover_cineflex,
            'remove_lidar_system': self.remover_lidar_system,
            'remove_af120': self.remover_af120,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'leulit.anotacion_technical_log',
            'view_mode': 'form',
            'res_id': anotacion.id,
            'target': 'current',
        }
