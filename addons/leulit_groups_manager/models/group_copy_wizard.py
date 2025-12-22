# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GroupCopyWizard(models.TransientModel):
    _name = 'leulit.group.copy.wizard'
    _description = 'Wizard para copiar elementos entre grupos'

    source_group_id = fields.Many2one(
        'res.groups',
        string='Grupo Origen',
        required=True,
        help='Grupo desde el que se copiarán los elementos'
    )
    
    target_group_id = fields.Many2one(
        'res.groups',
        string='Grupo Destino',
        required=True,
        help='Grupo al que se copiarán los elementos'
    )
    
    copy_type = fields.Selection([
        ('users', 'Usuarios'),
        ('menus', 'Menús'),
        ('access_rights', 'Permisos de Acceso'),
        ('record_rules', 'Reglas de Registro'),
    ], string='Tipo de Copia', required=True, default='users')
    
    copy_all = fields.Boolean(
        string='Copiar Todo',
        default=True,
        help='Si está marcado, copia todos los elementos. Si no, copia solo los seleccionados'
    )
    
    # Campos para selección específica
    user_ids = fields.Many2many(
        'res.users',
        'group_copy_wizard_users_rel',
        string='Usuarios a Copiar',
        help='Usuarios específicos a copiar (solo si "Copiar Todo" está desmarcado)'
    )
    
    menu_ids = fields.Many2many(
        'ir.ui.menu',
        'group_copy_wizard_menus_rel',
        string='Menús a Copiar',
        help='Menús específicos a copiar (solo si "Copiar Todo" está desmarcado)'
    )
    
    access_ids = fields.Many2many(
        'ir.model.access',
        'group_copy_wizard_access_rel',
        string='Permisos a Copiar',
        help='Permisos específicos a copiar (solo si "Copiar Todo" está desmarcado)'
    )
    
    rule_ids = fields.Many2many(
        'ir.rule',
        'group_copy_wizard_rules_rel',
        string='Reglas a Copiar',
        help='Reglas específicas a copiar (solo si "Copiar Todo" está desmarcado)'
    )
    
    # Campos computados para mostrar disponibles
    available_user_ids = fields.Many2many(
        'res.users',
        string='Usuarios Disponibles',
        compute='_compute_available_items',
        store=False
    )
    
    available_menu_ids = fields.Many2many(
        'ir.ui.menu',
        string='Menús Disponibles',
        compute='_compute_available_items',
        store=False
    )
    
    available_access_ids = fields.Many2many(
        'ir.model.access',
        string='Permisos Disponibles',
        compute='_compute_available_items',
        store=False
    )
    
    available_rule_ids = fields.Many2many(
        'ir.rule',
        string='Reglas Disponibles',
        compute='_compute_available_items',
        store=False
    )
    
    # Estadísticas
    stats_info = fields.Html(
        string='Información',
        compute='_compute_stats_info',
        store=False
    )

    @api.depends('source_group_id', 'copy_type')
    def _compute_available_items(self):
        """Calcula elementos disponibles en el grupo origen"""
        for wizard in self:
            if not wizard.source_group_id:
                wizard.available_user_ids = False
                wizard.available_menu_ids = False
                wizard.available_access_ids = False
                wizard.available_rule_ids = False
                continue
                
            # Usuarios del grupo origen
            wizard.available_user_ids = wizard.source_group_id.users
            
            # Menús del grupo origen
            wizard.available_menu_ids = self.env['ir.ui.menu'].search([
                ('groups_id', 'in', wizard.source_group_id.id)
            ])
            
            # Permisos de acceso del grupo origen
            wizard.available_access_ids = self.env['ir.model.access'].search([
                ('group_id', '=', wizard.source_group_id.id)
            ])
            
            # Reglas de registro del grupo origen
            wizard.available_rule_ids = self.env['ir.rule'].sudo().search([
                ('groups', 'in', wizard.source_group_id.id)
            ])

    @api.depends('source_group_id', 'target_group_id', 'copy_type', 'copy_all',
                 'user_ids', 'menu_ids', 'access_ids', 'rule_ids')
    def _compute_stats_info(self):
        """Genera información estadística de la copia"""
        for wizard in self:
            if not wizard.source_group_id or not wizard.target_group_id:
                wizard.stats_info = '<p>Selecciona grupo origen y destino</p>'
                continue
            
            html = ['<div style="padding: 10px;">']
            html.append('<h4>📊 Resumen de la Copia</h4>')
            html.append(f'<p><strong>Origen:</strong> {wizard.source_group_id.name}</p>')
            html.append(f'<p><strong>Destino:</strong> {wizard.target_group_id.name}</p>')
            html.append(f'<p><strong>Tipo:</strong> {dict(wizard._fields["copy_type"].selection).get(wizard.copy_type)}</p>')
            
            if wizard.copy_type == 'users':
                total = len(wizard.available_user_ids)
                to_copy = total if wizard.copy_all else len(wizard.user_ids)
                html.append(f'<p><strong>Usuarios a copiar:</strong> {to_copy} de {total}</p>')
                
            elif wizard.copy_type == 'menus':
                total = len(wizard.available_menu_ids)
                to_copy = total if wizard.copy_all else len(wizard.menu_ids)
                html.append(f'<p><strong>Menús a copiar:</strong> {to_copy} de {total}</p>')
                
            elif wizard.copy_type == 'access_rights':
                total = len(wizard.available_access_ids)
                to_copy = total if wizard.copy_all else len(wizard.access_ids)
                html.append(f'<p><strong>Permisos a copiar:</strong> {to_copy} de {total}</p>')
                
            elif wizard.copy_type == 'record_rules':
                total = len(wizard.available_rule_ids)
                to_copy = total if wizard.copy_all else len(wizard.rule_ids)
                html.append(f'<p><strong>Reglas a copiar:</strong> {to_copy} de {total}</p>')
            
            html.append('</div>')
            wizard.stats_info = ''.join(html)

    @api.onchange('source_group_id')
    def _onchange_source_group(self):
        """Limpiar selección al cambiar grupo origen"""
        self.user_ids = False
        self.menu_ids = False
        self.access_ids = False
        self.rule_ids = False

    @api.onchange('copy_type')
    def _onchange_copy_type(self):
        """Resetear selección al cambiar tipo"""
        self.copy_all = True
        self.user_ids = False
        self.menu_ids = False
        self.access_ids = False
        self.rule_ids = False

    def action_copy(self):
        """Ejecuta la copia según configuración"""
        self.ensure_one()
        
        if not self.source_group_id or not self.target_group_id:
            raise UserError(_('Debes seleccionar grupo origen y destino'))
        
        if self.source_group_id == self.target_group_id:
            raise UserError(_('El grupo origen y destino no pueden ser el mismo'))
        
        if self.copy_type == 'users':
            return self._copy_users()
        elif self.copy_type == 'menus':
            return self._copy_menus()
        elif self.copy_type == 'access_rights':
            return self._copy_access_rights()
        elif self.copy_type == 'record_rules':
            return self._copy_record_rules()

    def _copy_users(self):
        """Copia usuarios del grupo origen al destino"""
        if self.copy_all:
            users_to_copy = self.available_user_ids
        else:
            if not self.user_ids:
                raise UserError(_('Debes seleccionar al menos un usuario'))
            users_to_copy = self.user_ids
        
        # Añadir grupo destino a los usuarios
        for user in users_to_copy:
            if self.target_group_id not in user.groups_id:
                user.write({'groups_id': [(4, self.target_group_id.id)]})
        
        return self._show_success_message(
            _('Usuarios Copiados'),
            _('%d usuarios han sido añadidos al grupo "%s"') % (
                len(users_to_copy), self.target_group_id.name
            )
        )

    def _copy_menus(self):
        """Copia menús del grupo origen al destino"""
        if self.copy_all:
            menus_to_copy = self.available_menu_ids
        else:
            if not self.menu_ids:
                raise UserError(_('Debes seleccionar al menos un menú'))
            menus_to_copy = self.menu_ids
        
        # Añadir grupo destino a los menús
        for menu in menus_to_copy:
            if self.target_group_id not in menu.groups_id:
                menu.write({'groups_id': [(4, self.target_group_id.id)]})
        
        return self._show_success_message(
            _('Menús Copiados'),
            _('%d menús han sido asociados al grupo "%s"') % (
                len(menus_to_copy), self.target_group_id.name
            )
        )

    def _copy_access_rights(self):
        """Copia permisos de acceso del grupo origen al destino"""
        if self.copy_all:
            access_to_copy = self.available_access_ids
        else:
            if not self.access_ids:
                raise UserError(_('Debes seleccionar al menos un permiso'))
            access_to_copy = self.access_ids
        
        created_count = 0
        for access in access_to_copy:
            # Verificar si ya existe un permiso para este modelo y grupo destino
            existing = self.env['ir.model.access'].search([
                ('model_id', '=', access.model_id.id),
                ('group_id', '=', self.target_group_id.id)
            ], limit=1)
            
            if not existing:
                # Crear nuevo permiso de acceso
                self.env['ir.model.access'].create({
                    'name': f'{access.model_id.model} {self.target_group_id.name}',
                    'model_id': access.model_id.id,
                    'group_id': self.target_group_id.id,
                    'perm_read': access.perm_read,
                    'perm_write': access.perm_write,
                    'perm_create': access.perm_create,
                    'perm_unlink': access.perm_unlink,
                })
                created_count += 1
        
        return self._show_success_message(
            _('Permisos Copiados'),
            _('%d permisos de acceso han sido copiados al grupo "%s" (%d ya existían)') % (
                created_count, self.target_group_id.name, len(access_to_copy) - created_count
            )
        )

    def _copy_record_rules(self):
        """Copia reglas de registro del grupo origen al destino"""
        if self.copy_all:
            rules_to_copy = self.available_rule_ids
        else:
            if not self.rule_ids:
                raise UserError(_('Debes seleccionar al menos una regla'))
            rules_to_copy = self.rule_ids
        
        # Añadir grupo destino a las reglas
        for rule in rules_to_copy.sudo():
            if self.target_group_id not in rule.groups:
                rule.write({'groups': [(4, self.target_group_id.id)]})
        
        return self._show_success_message(
            _('Reglas Copiadas'),
            _('%d reglas de registro han sido asociadas al grupo "%s"') % (
                len(rules_to_copy), self.target_group_id.name
            )
        )

    def _show_success_message(self, title, message):
        """Muestra mensaje de éxito y cierra el wizard"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
