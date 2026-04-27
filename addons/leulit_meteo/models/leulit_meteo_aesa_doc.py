# -*- coding: utf-8 -*-
import base64
import os

from odoo import fields, models, _


class LeulitMeteoAesaDoc(models.TransientModel):
    _name = 'leulit.meteo.aesa.doc'
    _description = 'Documento de Conformidad AESA'

    contenido_html = fields.Html(
        string='Contenido', readonly=True,
        default=lambda self: self._html_content())

    @staticmethod
    def _html_content():
        """Lee el fichero AESA_COMPLIANCE.html."""
        html_path = os.path.join(os.path.dirname(__file__), '..', 'AESA_COMPLIANCE.html')
        try:
            with open(html_path, encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return '<p>Documento no encontrado.</p>'

    def action_download_md(self):
        """Descarga el fichero AESA_COMPLIANCE.html."""
        self.ensure_one()
        html_path = os.path.join(os.path.dirname(__file__), '..', 'AESA_COMPLIANCE.html')
        with open(html_path, 'rb') as f:
            content = base64.b64encode(f.read())
        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'AESA_Compliance_Leulit_Meteo.html',
            'datas': content,
            'mimetype': 'text/html',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_print_pdf(self):
        """Genera el PDF del documento de conformidad AESA."""
        self.ensure_one()
        return self.env.ref('leulit_meteo.report_aesa_compliance').report_action(self)
