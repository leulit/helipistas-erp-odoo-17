# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_wizard_report_curso(models.TransientModel):
    _name = "leulit.wizard_report_curso"
    _description = "leulit_wizard_report_curso"

    #def buildpdf_wrc(self, cr, uid, cursosid, piloto_id, alumnonombre, alumnoapellidos,alumnofirma, nameperfil, context):
    #    data = self.pool.get('helipistas.wizard_report_alumno_curso').getDataPdf(cr, uid, cursosid, piloto_id, alumnonombre, alumnoapellidos, alumnofirma, nameperfil, context)
    #    return {
    #        'type': 'ir.actions.report.xml',
    #        'report_name': 'hlp_202008131245_report',
    #        'datas': {
    #            'model': 'helipistas.wizard_report_curso',
    #            'ids': [],
    #            'report_type': "pdf",
    #            'form': data
    #        },
    #        'nodestroy': True,
    #        'context': context
    #    }


    def imprimir(self):
    #    if context is None:
    #        context = {}
    #    firma=False
    #    for item in self.browse(cr, uid, ids, context):
    #        cursosid = []
    #        for curso in item.cursos:
    #            cursosid.append( curso.curso_id.id)

    #        if item.alumno.firma_user:
    #            firma = item.alumno.firma_user
    #        else:
    #            if item.alumno.piloto_id.firma_user:
    #                firma = item.alumno.piloto_id.firma_user
        #TODO:----
    #    return self.buildpdf_wrc(cr, uid, cursosid, item.alumno.piloto_id.id, item.alumno.apellidos, item.alumno.nombre, firma, '', context)
        raise UserError('Funcionalidad no migrada boton')


    alumno = fields.Many2one(comodel_name='leulit.alumno', string='Alumno')
    cursos = fields.Many2many('leulit.rel_alumno_curso', relation='leulit_relation_003', column1='popup_rel', column2='curso_id', string='Cursos', required=True)
    
    
    