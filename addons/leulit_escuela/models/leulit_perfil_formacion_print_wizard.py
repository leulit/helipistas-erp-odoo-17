# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class leulit_perfil_formacion_print_wizard(models.TransientModel):
    _name           = "leulit.perfil_formacion_print_wizard"
    _description    = "leulit_perfil_formacion_print_wizard"

    def pf_print_wizard(self):
        for item in self:    
            idscursos = []
            for pfcurso in item.perfil_formacion.cursos:
                items = self.env['leulit.perfil_formacion_curso_last_done'].search([('pf_curso', '=', pfcurso.id),('done_date','>=',item.from_date),('done_date','<=',item.to_date)])
                for i in range(0, len(items)):
                    if (i+1) < len(items):
                        fecha_ini = items[i+1].done_date
                    else:
                        fecha_ini = '2001-01-01'
                    valido_hasta = items[i].pf_curso._calculateNextDoneDate(items[i].pf_curso.periodicidad_dy, items[i].done_date)
                    idscursos.append({
                        'fecha_ini'     : fecha_ini,
                        'fecha_fin'     : items[i].done_date,
                        'valido_desde'  : items[i].done_date,
                        'valido_hasta'  : valido_hasta,
                        'curso'         : pfcurso.curso
                    })
            data = self.env['leulit.report_curso_pf'].getDataPdf(idscursos, item.perfil_formacion.alumno, "")
            return self.env.ref('leulit_escuela.report_curso_pf').report_action(self,data=data)


    perfil_formacion = fields.Many2one(comodel_name='leulit.perfil_formacion',string='Perfil Formación')
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')

