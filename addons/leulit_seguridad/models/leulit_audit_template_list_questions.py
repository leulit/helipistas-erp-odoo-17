# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)



class LeulitAuditTemplateListQuestions(models.Model):
    _name = "leulit.audit_template_list_questions"
    _description = 'Plantilla de Lista de Preguntas de Auditoría'


    name = fields.Char(string="Nombre")