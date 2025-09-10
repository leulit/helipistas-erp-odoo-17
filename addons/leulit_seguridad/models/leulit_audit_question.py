# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitAuditQuestion(models.Model):
    _name = "leulit.audit_question"


    def unlink(self):
        for item in self:
            if item.editable:
                return super().unlink()
            else:
                raise UserError('No se puede eliminar una pregunta que ya ha sido utilizada en una auditoría')

    @api.depends()
    def _get_semaforo(self):
        for item in self:
            hoy = datetime.now().date()
            año = hoy.year
            start_año_actual = datetime.strptime("{0}-01-01".format(año),"%Y-%m-%d").date()
            end_año_actual = datetime.strptime("{0}-12-31".format(año),"%Y-%m-%d").date()
            item.semaforo = 'red'
            for line in self.env['mgmtsystem.verification.line'].search([('question_id', '=', item.id)]):
                if line.audit_id.date:
                    if line.audit_id.date.date() >= start_año_actual and line.audit_id.date.date() <= end_año_actual:
                        item.semaforo = 'green'

    def _get_is_editable(self):
        for item in self:
            item.editable = True
            if len(self.env['mgmtsystem.verification.line'].search([('question_id', '=', item.id)]).ids) > 0: 
                item.editable = False

    name = fields.Char(string="Pregunta", required=True)
    sequence = fields.Integer(string="Secuencia")
    norma = fields.Char(string="Norma")
    procedure_id = fields.Many2one(comodel_name="leulit.procedure_audit_question", string="Procedimiento", required=True)
    recurrencia = fields.Float(string="Recurrencia")
    area_ids = fields.Many2many('hr.department', string='Area', ondelete='restrict')
    estado = fields.Selection([('borrador', 'Borrador'), ('en_vigor', 'En vigor'), ('cancelado', 'Cancelado')], default='borrador', string="Estado")
    notas = fields.Text(string="Notas")
    semaforo = fields.Char(compute=_get_semaforo, string="")
    editable = fields.Boolean(compute=_get_is_editable , string="Editable")
