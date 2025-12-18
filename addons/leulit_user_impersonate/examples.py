# -*- coding: utf-8 -*-
# User Impersonation Module - Quick Start Examples

"""
Este archivo contiene ejemplos de uso del módulo de impersonación.
NO es necesario para el funcionamiento del módulo, solo para referencia.
"""

# ==============================================================================
# EJEMPLO 1: Impersonar un usuario desde código Python
# ==============================================================================

def example_impersonate_from_code(self):
    """
    Ejemplo de cómo iniciar una impersonación programáticamente.
    Nota: Esto normalmente se hace desde la UI, este es solo un ejemplo.
    """
    # Obtener el usuario a impersonar
    target_user = self.env['res.users'].search([('login', '=', 'demo')], limit=1)
    
    if target_user:
        # Llamar al método de impersonación
        action = target_user.action_impersonate_user()
        # Esto devuelve una acción cliente que debe ser ejecutada en el frontend
        return action


# ==============================================================================
# EJEMPLO 2: Verificar si un usuario está siendo impersonado
# ==============================================================================

def example_check_impersonation(self):
    """
    Ejemplo de cómo verificar si el usuario actual está siendo impersonado.
    Útil para logging o auditoría adicional.
    """
    # Desde la sesión HTTP (en un controlador)
    from odoo import http
    if http.request.session.get('impersonate_original_uid'):
        original_uid = http.request.session['impersonate_original_uid']
        current_uid = http.request.session.uid
        print(f"Usuario {original_uid} impersonando a {current_uid}")
        return True
    return False


# ==============================================================================
# EJEMPLO 3: Obtener historial de impersonaciones de un usuario
# ==============================================================================

def example_get_user_impersonation_history(self, user_id):
    """
    Obtener todas las veces que un usuario ha sido impersonado.
    Útil para auditoría.
    """
    impersonate_logs = self.env['impersonate.log'].search([
        ('impersonated_user_id', '=', user_id)
    ], order='start_date desc')
    
    history = []
    for log in impersonate_logs:
        history.append({
            'date': log.start_date,
            'impersonator': log.original_user_id.name,
            'duration': log.duration,
        })
    
    return history


# ==============================================================================
# EJEMPLO 4: Restricción personalizada - No permitir impersonar managers
# ==============================================================================

def example_custom_restriction(self):
    """
    Ejemplo de cómo añadir restricciones personalizadas.
    Esto se haría heredando el método action_impersonate_user en res.users
    """
    from odoo import models, _
    from odoo.exceptions import UserError
    
    class ResUsersCustom(models.Model):
        _inherit = 'res.users'
        
        def action_impersonate_user(self):
            # Restricción personalizada: no permitir impersonar a managers
            if self.has_group('base.group_system'):
                raise UserError(_(
                    'Cannot impersonate system administrators or managers.'
                ))
            
            # Llamar al método original
            return super(ResUsersCustom, self).action_impersonate_user()


# ==============================================================================
# EJEMPLO 5: Notificar al usuario que está siendo impersonado (opcional)
# ==============================================================================

def example_notify_impersonated_user(self):
    """
    Ejemplo de cómo notificar al usuario que está siendo impersonado.
    Esto es opcional y puede ser deshabilitado por privacidad.
    """
    from odoo import models
    
    class ResUsersNotify(models.Model):
        _inherit = 'res.users'
        
        def action_impersonate_user(self):
            result = super(ResUsersNotify, self).action_impersonate_user()
            
            # Enviar notificación (opcional)
            self.env['mail.message'].create({
                'message_type': 'notification',
                'subject': 'Your account is being impersonated',
                'body': f'User {self.env.user.name} is viewing Odoo as you.',
                'partner_ids': [(4, self.partner_id.id)],
            })
            
            return result


# ==============================================================================
# EJEMPLO 6: Widget personalizado para mostrar estado en formularios
# ==============================================================================

"""
<!-- En una vista XML personalizada -->
<xpath expr="//header" position="before">
    <div class="alert alert-warning" 
         invisible="not is_impersonating">
        <strong>Warning:</strong> You are viewing this as an impersonated user.
    </div>
</xpath>
"""


# ==============================================================================
# EJEMPLO 7: Restricción por tiempo - Auto-cerrar después de 1 hora
# ==============================================================================

def example_time_limited_impersonation(self):
    """
    Ejemplo de cómo implementar impersonación con límite de tiempo.
    Requeriría un cron job que verifique y cierre sesiones antiguas.
    """
    from datetime import datetime, timedelta
    
    # En un cron job (scheduled action)
    def close_expired_impersonations():
        # Buscar sesiones activas de más de 1 hora
        one_hour_ago = datetime.now() - timedelta(hours=1)
        expired_logs = self.env['impersonate.log'].search([
            ('end_date', '=', False),
            ('start_date', '<', one_hour_ago),
        ])
        
        for log in expired_logs:
            # Cerrar la sesión
            log.write({'end_date': datetime.now()})
            # Aquí podrías forzar el logout de la sesión HTTP si es necesario


# ==============================================================================
# EJEMPLO 8: Audit trail extendido - Registrar acciones durante impersonación
# ==============================================================================

def example_extended_audit_trail(self):
    """
    Ejemplo de cómo registrar todas las acciones realizadas durante impersonación.
    Esto requeriría heredar ir.model y sobrescribir write/create.
    """
    from odoo import models
    
    class IrModelAudit(models.Model):
        _inherit = 'ir.model'
        
        def write(self, vals):
            # Verificar si hay impersonación activa
            from odoo import http
            try:
                original_uid = http.request.session.get('impersonate_original_uid')
                if original_uid:
                    # Registrar la acción
                    self.env['impersonate.action.log'].sudo().create({
                        'original_user_id': original_uid,
                        'impersonated_user_id': http.request.session.uid,
                        'model': self._name,
                        'action': 'write',
                        'record_id': self.id,
                        'values': str(vals),
                    })
            except:
                pass  # No hay sesión HTTP (ej. desde cron)
            
            return super(IrModelAudit, self).write(vals)


# ==============================================================================
# TESTING
# ==============================================================================

def run_tests():
    """
    Ejecutar estos tests después de instalar el módulo.
    
    En Odoo shell:
    >>> from odoo.addons.leulit_user_impersonate import examples
    >>> examples.run_tests()
    """
    print("Tests not implemented yet. Use manual testing:")
    print("1. Login as admin")
    print("2. Go to Settings → Users")
    print("3. Open any user form")
    print("4. Click 'Impersonate User'")
    print("5. Verify banner appears")
    print("6. Click 'Stop Impersonation'")
    print("7. Verify you're back to your user")
