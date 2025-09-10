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


class leulit_perfil_formacion_curso_last_done(models.Model):
    _inherit = "leulit.perfil_formacion_curso_last_done"


    def firmar_informe_general_cursos_alu_ld(self):
        for item in self:
            pdfAction = self.getdata_informe_general_cursos_alu_ld()
            pdfAction['date_hashcode'] = utilitylib.getStrTodayFullIsoFormat()
            hashdata = utilitylib.getHashOfData(pdfAction)
            hashcode = "PF-{0}".format(hashdata)
            pdfAction['csv_cid'] = hashcode
            pdfAction['firmado_por'] = self.env.user.name
            
            report_name = 'leulit_escuela.report_curso_pf'
            pdf = self.env.ref(report_name)._render_qweb_pdf([],pdfAction)[0]
            report = base64.encodestring(pdf)

            descripcion = "{0}. Curso {1}".format( item.alumno.name, item.pf_curso.curso.name )
            
            iddoc = self.env['leulit.alumno'].buildDocPracticasFirmado1Step(item.alumno.id, descripcion, utilitylib.getStrToday(), report, hashcode)
            return self.env['leulit_signaturedoc'].popUpDescargaDocFirmado(iddoc)  