# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import timedelta

import logging
import base64
import io
try:
    from PyPDF2 import PdfMerger
except Exception:
    PdfMerger = None
_logger = logging.getLogger(__name__)


class leulit_wizard_report_experiencia(models.TransientModel):
    _name           = "leulit.wizard_report_experiencia"
    _description    = "leulit_wizard_report_experiencia"


    mecanico_id = fields.Many2one(comodel_name='leulit.mecanico', string='Mecánico')
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')



    def print_report_experiencia(self):
        company_icarus = self.env['res.company'].search([('name','like','Icarus')])

        # Recolectar items (pequeña lista de dicts) — cada dict representa una fila del informe
        items = []
        records = self.env['leulit.item_experiencia_mecanico'].search([
            ('mecanico_id', '=', self.mecanico_id.id),
            ('date', '>=', self.from_date),
            ('date', '<=', self.to_date)
        ])
        for rec in records:
            for items_diff_atas in rec.get_data_to_report():
                items.append(items_diff_atas)

        items_per_page = 8
        total_items = len(items)
        remaining_items = items_per_page - (total_items % items_per_page) if total_items % items_per_page != 0 else 0

        empty_item = {
            'date': '', 'location': '', 'ac_type': '', 'ac_comp': '', 'type_maintenance': '', 'privilege': '',
            'fot': '', 'sgh': '', 'ri': '', 'ts': '', 'mod': '', 'rep': '', 'insp': '', 'training': '',
            'perform': '', 'supervise': '', 'crs': '', 'ata_ids': '', 'operation_performed': '', 'duration': '',
            'maintenance_record_ref': '', 'remarks': '',
        }

        items.extend([empty_item.copy() for _ in range(remaining_items)])
        pages = [items[i:i + items_per_page] for i in range(0, len(items), items_per_page)]

        if not pages:
            raise UserError(_('No hay datos para generar el informe en el rango indicado.'))

        report_ref = self.env.ref('leulit_actividad_taller.leulit_20240521_1012_report')

        # Render por lotes de páginas para controlar memoria
        CHUNK_PAGES = 10
        pdf_parts = []
        for i in range(0, len(pages), CHUNK_PAGES):
            pages_slice = pages[i:i + CHUNK_PAGES]
            datos = {
                'logo_ica': company_icarus.logo_reports,
                'mecanico': self.mecanico_id.name if self.mecanico_id else '',
                'pages': pages_slice,
                'from_date': self.from_date.strftime('%d/%m/%Y') if self.from_date else '',
                'to_date': self.to_date.strftime('%d/%m/%Y') if self.to_date else '',
                'total_pages': len(pages)
            }
            # _render_qweb_pdf devuelve tupla (pdf_bytes, content_type)
            pdf_bytes = report_ref._render_qweb_pdf([], data=datos)[0]
            pdf_parts.append(pdf_bytes)

        # Si hay una sola parte, devolverla directamente
        if len(pdf_parts) == 1:
            # crear attachment para descarga consistente
            merged = pdf_parts[0]
        else:
            if PdfMerger is None:
                raise UserError(_('PyPDF2 no está instalado en el servidor. Instala PyPDF2 para permitir fusión de PDFs en memoria.'))
            merger = PdfMerger()
            for part in pdf_parts:
                merger.append(io.BytesIO(part))
            out = io.BytesIO()
            merger.write(out)
            merger.close()
            merged = out.getvalue()

        # Crear attachment y devolver URL de descarga
        import time
        fname = 'experiencia_%s_%s.pdf' % (self.mecanico_id.id if self.mecanico_id else 'unknown', datetime.now().strftime('%Y%m%d%H%M%S'))
        attach_vals = {
            'name': fname,
            'type': 'binary',
            'datas': base64.b64encode(merged).decode('utf-8'),
            'mimetype': 'application/pdf',
        }
        attachment = self.env['ir.attachment'].create(attach_vals)
        url = '/web/content/%s?model=ir.attachment&field=datas&download=true' % attachment.id
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }