# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_informes_historial_popup(models.TransientModel):
    _name           = "leulit.informes_historial_popup"
    _description    = "leulit_informes_historial_popup"


    def imprimir_seleccion_historial(self):
        return self.env.ref('leulit_escuela.informes_historial_popup_report').report_action(self)

    
    date_from = fields.Date('Fecha inicio', required=True)
    date_to = fields.Date('Fecha fin', required=True)
    alumno_id = fields.Many2one(comodel_name='leulit.piloto', string='Alumno')
    soloteoricas = fields.Boolean('Solo teóricas')



    
class report_leulit_escuela_informes_historial_popup_report(models.AbstractModel):
    _name = 'report.leulit_escuela.leulit_20211014_1131_informe'
    _description = 'Informe de Historial de Escuela'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['leulit.informes_historial_popup'].browse(docids)
        datos = {}

        for item in docs:
            if item.soloteoricas:
                idspartes = self.env['leulit.parte_escuela'].search([('alumnos', 'in', [item.alumno_id.id]),('vuelo_id', '=', False), ('fecha', '>=', item.date_from),('fecha', '<=', item.date_to)])
            else:
                idspartes = self.env['leulit.parte_escuela'].search([('alumnos', 'in', [item.alumno_id.id]),('fecha', '>=', item.date_from),('fecha', '<=', item.date_to)])
            datos['partes'] = idspartes

        return {
            'doc_ids' : docids,
            'docs' : docs,
            'data' : datos,
            }
