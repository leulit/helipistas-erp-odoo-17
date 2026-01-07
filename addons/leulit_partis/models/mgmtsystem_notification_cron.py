# -*- coding: utf-8 -*-
"""
Sistema de notificaciones automáticas para gestión de riesgos.
Envía alertas sobre riesgos pendientes de revisión y riesgos críticos sin tratamiento.
Cumple con IS.D.OR.305 (Mejora continua y alertas).
"""

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.tools import email_normalize


class MgmtsystemNotificationCron(models.Model):
    _name = 'mgmtsystem.notification.cron'
    _description = 'Configuración de Notificaciones Automáticas'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(string='Activo', default=True)
    notification_type = fields.Selection([
        ('pending_approval', 'Riesgos Pendientes de Aprobación'),
        ('critical_risks', 'Riesgos Críticos sin Tratamiento'),
    ], string='Tipo de Notificación', required=True)
    days_threshold = fields.Integer(
        string='Días de Antigüedad',
        default=3,
        help='Notificar si los registros tienen más de X días'
    )
    recipient_group_id = fields.Many2one(
        'res.groups',
        string='Grupo Destinatario',
        help='Grupo de usuarios que recibirán la notificación'
    )
    recipient_user_ids = fields.Many2many(
        'res.users',
        string='Destinatarios Adicionales',
        help='Usuarios adicionales que recibirán la notificación'
    )
    last_run_date = fields.Datetime(string='Última Ejecución', readonly=True)
    last_notification_count = fields.Integer(string='Alertas Enviadas', readonly=True)

    @api.model
    def _cron_send_pending_approval_notifications(self):
        """
        Método cron para enviar notificaciones de riesgos pendientes de aprobación.
        Se ejecuta diariamente.
        """
        configs = self.search([
            ('active', '=', True),
            ('notification_type', '=', 'pending_approval')
        ])

        for config in configs:
            threshold_date = fields.Datetime.now() - timedelta(days=config.days_threshold)
            
            # Buscar riesgos pendientes
            pending_risks = self.env['mgmtsystem.risk'].search([
                ('treatment_plan_state', '=', 'pending'),
                ('create_date', '<=', threshold_date)
            ])

            if pending_risks:
                recipients = config._get_recipients()
                if recipients:
                    config._send_pending_approval_email(pending_risks, recipients)
                    config.write({
                        'last_run_date': fields.Datetime.now(),
                        'last_notification_count': len(pending_risks)
                    })

        return True

    @api.model
    def _cron_send_critical_risks_notifications(self):
        """
        Método cron para enviar notificaciones de riesgos críticos sin tratamiento.
        Se ejecuta semanalmente.
        """
        configs = self.search([
            ('active', '=', True),
            ('notification_type', '=', 'critical_risks')
        ])

        for config in configs:
            # Buscar riesgos críticos sin plan aprobado
            critical_risks = self.env['mgmtsystem.risk'].search([
                ('residual_level', 'in', [4, 5]),
                ('treatment_plan_state', 'in', ['draft', 'rejected']),
            ])

            if critical_risks:
                recipients = config._get_recipients()
                if recipients:
                    config._send_critical_risks_email(critical_risks, recipients)
                    config.write({
                        'last_run_date': fields.Datetime.now(),
                        'last_notification_count': len(critical_risks)
                    })

        return True

    def _get_recipients(self):
        """Obtener lista de destinatarios de email."""
        recipients = []
        
        # Agregar usuarios del grupo
        if self.recipient_group_id:
            recipients.extend(self.recipient_group_id.users.mapped('email'))
        
        # Agregar usuarios adicionales
        if self.recipient_user_ids:
            recipients.extend(self.recipient_user_ids.mapped('email'))
        
        # Filtrar emails válidos
        return [email_normalize(email) for email in recipients if email_normalize(email)]

    def _send_pending_approval_email(self, risks, recipients):
        """Enviar email sobre riesgos pendientes de aprobación."""
        template = self.env.ref('leulit_partis.email_template_pending_approval_risks', raise_if_not_found=False)
        if not template:
            return

        # Preparar contexto con información de los riesgos
        risk_list = []
        for risk in risks:
            risk_list.append({
                'asset': risk.hazard_id.name,
                'threat': risk.magerit_threat_id.name,
                'level': risk.residual_level,
                'days_pending': (fields.Datetime.now() - risk.create_date).days,
                'url': '/web#id={}&model=mgmtsystem.risk&view_type=form'.format(risk.id)
            })

        ctx = {
            'risk_count': len(risks),
            'risk_list': risk_list,
            'days_threshold': self.days_threshold,
        }

        # Enviar email a cada destinatario
        for email in recipients:
            template.with_context(ctx).send_mail(
                self.id,
                force_send=True,
                email_values={
                    'email_to': email,
                }
            )

    def _send_critical_risks_email(self, risks, recipients):
        """Enviar email sobre riesgos críticos sin tratamiento."""
        template = self.env.ref('leulit_partis.email_template_critical_risks', raise_if_not_found=False)
        if not template:
            return

        # Preparar contexto con información de los riesgos
        risk_list = []
        for risk in risks:
            risk_list.append({
                'asset': risk.hazard_id.name,
                'threat': risk.magerit_threat_id.name,
                'level': risk.residual_level,
                'state': dict(risk._fields['treatment_plan_state'].selection).get(risk.treatment_plan_state),
                'url': '/web#id={}&model=mgmtsystem.risk&view_type=form'.format(risk.id)
            })

        ctx = {
            'risk_count': len(risks),
            'risk_list': risk_list,
        }

        # Enviar email a cada destinatario
        for email in recipients:
            template.with_context(ctx).send_mail(
                self.id,
                force_send=True,
                email_values={
                    'email_to': email,
                }
            )
