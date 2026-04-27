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
        """Lee el fichero AESA_COMPLIANCE.md y lo convierte a HTML básico."""
        md_path = os.path.join(os.path.dirname(__file__), '..', 'AESA_COMPLIANCE.md')
        try:
            with open(md_path, encoding='utf-8') as f:
                md = f.read()
        except FileNotFoundError:
            return '<p>Documento no encontrado.</p>'

        try:
            import markdown
            return markdown.markdown(md, extensions=['tables', 'fenced_code'])
        except ImportError:
            pass

        # Conversión mínima sin librería externa
        import re
        html = md
        html = re.sub(r'^#{3} (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#{2} (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'^\| (.+)$', lambda m: '<tr>' + ''.join(
            f'<td>{c.strip()}</td>' for c in m.group(1).split('|')) + '</tr>', html, flags=re.MULTILINE)
        html = re.sub(r'^---+$', '<hr/>', html, flags=re.MULTILINE)
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = '\n'.join(
            line if line.startswith('<') else f'<p>{line}</p>' if line.strip() else ''
            for line in html.splitlines()
        )
        return html

    def action_download_md(self):
        """Descarga el fichero AESA_COMPLIANCE.md."""
        self.ensure_one()
        md_path = os.path.join(os.path.dirname(__file__), '..', 'AESA_COMPLIANCE.md')
        with open(md_path, 'rb') as f:
            content = base64.b64encode(f.read())
        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'AESA_Compliance_Leulit_Meteo.md',
            'datas': content,
            'mimetype': 'text/markdown',
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
