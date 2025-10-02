# Copyright (C) 2010 Savoir-faire Linux (<http://www.savoirfairelinux.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from datetime import datetime, date, time
import logging

_logger = logging.getLogger(__name__)


class MgmtsystemAudit(models.Model):
    _name = "mgmtsystem.audit"
    _inherit = "mgmtsystem.audit"


    def copy(self, default=None):
        new_auditoria = super(MgmtsystemAudit, self).copy()
        for line in self.line_ids:
            line.copy(default={'audit_id': new_auditoria.id})
        return new_auditoria


    @api.onchange('procedimiento_id')
    def onchange_procedimiento_questions(self):
        if self.procedimiento_id:
            _logger.error('info estoy pasando por aqui ')
            self.line_ids = [(5, 0, 0)]
            for line in self.procedimiento_id.questions_ids:
                self.env['mgmtsystem.verification.line'].create({
                    'seq': line.sequence,
                    'name': line.name,
                    'question_id': line.id,
                    'notas': line.notas,
                    'audit_id': self.id,
                })
                _logger.error('info estoy pasando por aqui 2')

    def button_close_informe(self):
        self.ensure_one()
        view = self.env.ref('leulit_seguridad.leulit_20241017_1115_form',raise_if_not_found=False)
        self.closing_date = datetime.now()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Informe de Cierre',
            'res_model': 'mgmtsystem.audit',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'res_id': self.id,
            'target': 'new',
        }

    def save_close(self):
        self.message_post(body=_("Auditoría cerrada"))
        self.write({"state": "done"})
        return {'type': 'ir.actions.act_window_close'}

    def button_open(self):
        self.message_post(body=_("Auditoría abierta"))
        return self.write({"state": "open"})

    def button_draft(self):
        self.message_post(body=_("Auditoría en borrador"))
        return self.write({"state": "draft"})
    
    
    state = fields.Selection([("draft", "Borrador"), ("open", "Open"), ("done", "Closed")], "State", default="draft")
    last_revision_norma = fields.Text(string='Última revisión norma')
    procedimiento_id = fields.Many2one(comodel_name="leulit.procedure_audit_question", string="Procedimiento")
    department_id = fields.Many2one(comodel_name="hr.department", string="Área")
    close_text = fields.Text(string="Redacción de cierre")
    closing_date = fields.Datetime("Fecha de cierre", readonly=False)
    responsible_department_id = fields.Many2one(comodel_name="hr.employee", string="Responsable de área")
    responsible_audit_id = fields.Many2one(comodel_name="hr.employee", string="Responsable de Auditorías")