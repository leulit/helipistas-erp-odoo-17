# -*- encoding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError

_MODELOS_CON_FECHA_LIMITE = ('project.task', 'mgmtsystem.action')


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.constrains('date_deadline', 'res_model', 'res_id')
    def _check_deadline_vs_parent(self):
        for activity in self:
            if (
                not activity.date_deadline
                or activity.res_model not in _MODELOS_CON_FECHA_LIMITE
                or not activity.res_id
            ):
                continue
            parent_model = self.env.get(activity.res_model)
            if parent_model is None:
                continue
            parent = parent_model.browse(activity.res_id)
            if not parent.exists() or not parent.date_deadline:
                continue
            if activity.date_deadline > parent.date_deadline:
                tipo = _("tarea") if activity.res_model == 'project.task' else _("acción")
                raise ValidationError(_(
                    "La fecha de vencimiento de la actividad (%s) no puede ser posterior "
                    "a la fecha límite de la %s (%s).",
                    activity.date_deadline,
                    tipo,
                    parent.date_deadline,
                ))

    def action_open_source_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_("Esta actividad no tiene un documento fuente asociado."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
