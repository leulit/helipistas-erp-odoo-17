# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)



class LeulitProcedureAuditQuestion(models.Model):
    _name = "leulit.procedure_audit_question"
    _description = 'Pregunta de Auditoría de Procedimiento'


    name = fields.Char(string="Nombre")
    questions_ids = fields.One2many(comodel_name="leulit.audit_question", inverse_name="procedure_id", string="Preguntas")
    # line_ids = fields.One2many(comodel_name="leulit.list_questions", inverse_name="audit_template_list_questions_id", string="Verification List")



