# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64

_logger = logging.getLogger(__name__)


class leulit_wizard_report_teoricas_curso(models.TransientModel):
    _inherit = "leulit.wizard_report_teoricas_curso"    


    def firmar(self):
        for item in self:
            datos = self.build_report(True)
            report_service = 'leulit_escuela.wizard_report_teoricas_curso_report'
            pdf = self.env.ref(report_service)._render_qweb_pdf([],datos)[0] 

            report = base64.b64encode(pdf)   
            idsCursos = []
            for curso in item.cursos:
                idsCursos.append(curso.curso_id.id)
            cursos = utilitylib.listToStr(idsCursos)
            descripcion = "{0}. Cursos: [{1}]".format( item.alumno.name, cursos )
            iddoc = item.alumno.buildDocTeoricasFirmado1Step(descripcion, utilitylib.getStrToday(), report, datos['hashcode'])
            return self.env['leulit_signaturedoc'].popUpDescargaDocFirmado(iddoc)          