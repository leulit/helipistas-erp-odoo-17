# -*- encoding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    date_history_ids = fields.One2many(
        comodel_name='leulit.activity.date.history',
        inverse_name='activity_id',
        string='Histórico de fechas'
    )

    def write(self, vals):
        if 'date_deadline' in vals:
            for record in self:
                if record.date_deadline and record.date_deadline != vals['date_deadline']:
                    self.env['leulit.activity.date.history'].create({
                        'activity_id': record.id,
                        'fecha_anterior': record.date_deadline,
                        'fecha_nueva': vals['date_deadline'],
                        'usuario_id': self.env.uid,
                    })
        return super(MailActivity, self).write(vals)
