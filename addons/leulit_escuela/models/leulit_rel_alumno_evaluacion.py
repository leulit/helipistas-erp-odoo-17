# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime,date,time
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_rel_alumno_evaluacion(models.Model):
    _name = "leulit.rel_alumno_evaluacion"
    _description = "leulit_rel_alumno_evaluacion"

    @api.depends('nota')
    def _get_apto(self):
        for item in self:
            item.apto = item.nota >= 75


    alumno_id = fields.Many2one('leulit.alumno', 'Alumno', required=True)
    fecha = fields.Date("Fecha")
    resultado = fields.Text("Resultado")
    nota = fields.Float("Nota %")
    asignatura = fields.Many2one('leulit.asignatura', 'Asignatura')
    apto = fields.Boolean(compute=_get_apto,string="Apto")
    tipo = fields.Selection([('interno', 'Interno'), ('externo', 'Externo')], 'Tipo')
    descripcion = fields.Text('Descripción')
    create_uid = fields.Many2one('res.users', 'created by User', readonly=True)
    documentos_examen = fields.Many2many('ir.attachment', 'leulit_examen_alumno_rel','examen_rel','doc_rel','Documentos')