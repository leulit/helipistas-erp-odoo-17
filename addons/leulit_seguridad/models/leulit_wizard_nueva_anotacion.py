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

    instalar_floats = fields.Boolean('Floats')
    instalar_dual_control = fields.Boolean('Dual control')
    instalar_cargo_hook_mirror = fields.Boolean('Cargo hook and mirror')
    instalar_life_raft = fields.Boolean('Life raft')
    instalar_life_vests_qty = fields.Integer('Life vests qty')
    instalar_headsets_qty = fields.Integer('Headsets qty')

    remover_floats = fields.Boolean('Floats')
    remover_dual_control = fields.Boolean('Dual control')
    remover_cargo_hook_mirror = fields.Boolean('Cargo hook and mirror')
    remover_life_raft = fields.Boolean('Life raft')
    remover_life_vests_qty = fields.Integer('Life vests qty')
    remover_headsets_qty = fields.Integer('Headsets qty')

    anotacion = fields.Text('Annotation')

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
        'remover_floats', 'remover_dual_control', 'remover_cargo_hook_mirror', 'remover_life_raft',
        'remover_life_vests_qty', 'remover_headsets_qty'
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
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'leulit.anotacion_technical_log',
            'view_mode': 'form',
            'res_id': anotacion.id,
            'target': 'current',
        }
