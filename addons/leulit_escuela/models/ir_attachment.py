# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
#TODO BeyondCompare from openerp.addons.hlp_ventas.SaleOrder import SaleOrder

_logger = logging.getLogger(__name__)


class ir_attachment(models.Model):
    _inherit = 'ir.attachment'
    
    doc_perfil_formacion = fields.Many2many('leulit.perfil_formacion_curso_last_done', 'leulit_perfil_rel','doc_rel','perfil_rel','REL')
    # doc_auditoria = fields.Many2many('leulit.auditoria', 'leulit_auditoria_rel','doc_rel','auditoria_rel','REL')
    doc_examen = fields.Many2many('leulit.rel_alumno_evaluacion', 'leulit_examen_alumno_rel','doc_rel','examen_rel','REL')
    doc_alumno = fields.Many2many('leulit.rel_alumno_documentacion', 'leulit_alumno_rel','doc_rel','alumno_rel','REL')
    rel_parte_escuela = fields.Many2one('leulit.rel_parte_escuela_cursos_alumnos', 'Rel Parte Escuela')
