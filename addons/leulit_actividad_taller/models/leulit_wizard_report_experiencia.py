# -*- encoding: utf-8 -*-

import base64
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import timedelta

import logging
_logger = logging.getLogger(__name__)



class leulit_wizard_report_experiencia(models.TransientModel):
    _name = "leulit.wizard_report_experiencia"
    _description = "leulit_wizard_report_experiencia"

    mecanico_id = fields.Many2one(comodel_name='leulit.mecanico', string='Mecánico')
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')
    pdf_file = fields.Binary(string="PDF generado")

    def print_report_experiencia(self):
        company_icarus = self.env['res.company'].search([('name','like','Icarus')])
        items = self.env['leulit.item_experiencia_mecanico'].search([
            ('mecanico_id', '=', self.mecanico_id.id),
            ('date', '>=', self.from_date),
            ('date', '<=', self.to_date)
        ])
        datos = {
            'logo_ica': company_icarus.logo_reports.decode(),
            'mecanico': self.mecanico_id.name if self.mecanico_id else '',
            'from_date': self.from_date.strftime('%d/%m/%Y') if self.from_date else '',
            'to_date': self.to_date.strftime('%d/%m/%Y') if self.to_date else '',
        }
        _logger.error('Datos para el reporte: %s', datos)
        _logger.error('Items para el reporte: %s', items)

        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            'leulit_actividad_taller.leulit_20240521_1012_informe',
            items.ids,
            data=datos
        )
        self.pdf_file = base64.b64encode(pdf_content)
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=leulit.wizard_report_experiencia&id=%s&field=pdf_file&download=true&filename=Informe_Experiencia.pdf' % self.id,
            'target': 'self',
        }