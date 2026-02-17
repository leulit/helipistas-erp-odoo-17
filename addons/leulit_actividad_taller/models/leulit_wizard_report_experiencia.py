# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import timedelta

import logging
import base64
import io
from pypdf import PdfWriter, PdfReader
import threading
from odoo import api, SUPERUSER_ID, registry as oregistry
_logger = logging.getLogger(__name__)


class leulit_wizard_report_experiencia(models.TransientModel):
    _name           = "leulit.wizard_report_experiencia"
    _description    = "leulit_wizard_report_experiencia"


    mecanico_id = fields.Many2one(comodel_name='leulit.mecanico', string='Mecánico')
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')
    pdf_merged = fields.Binary()
    pdf_filename = fields.Char()


    def merge_pdfs(self, pdf_list):
        pdf_writer = PdfWriter()

        for pdf_data in pdf_list:
            pdf_reader = PdfReader(io.BytesIO(pdf_data))
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                pdf_writer.add_page(page)

        # Crear un objeto BytesIO para almacenar el PDF combinado en memoria
        combined_pdf = io.BytesIO()
        pdf_writer.write(combined_pdf)

        # Posiciona el puntero al inicio del archivo
        combined_pdf.seek(0)
        return combined_pdf


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

        report_xmlid = 'leulit_actividad_taller.leulit_20240521_1012_report'

        # Render por lotes de páginas para controlar memoria
        CHUNK_PAGES = 10
        pdf_parts = []
        for i in range(0, len(pages), CHUNK_PAGES):
            pages_slice = pages[i:i + CHUNK_PAGES]
            datos = {
                'logo_ica': company_icarus.logo_reports.decode(),
                'mecanico': self.mecanico_id.name if self.mecanico_id else '',
                'pages': pages_slice,
                'from_date': self.from_date.strftime('%d/%m/%Y') if self.from_date else '',
                'to_date': self.to_date.strftime('%d/%m/%Y') if self.to_date else '',
                'total_pages': len(pages)
            }
            # _render_qweb_pdf devuelve tupla (pdf_bytes, content_type)
            # pasar el xmlid como primer argumento (forma esperada por algunas sobrecargas)
            pdf_bytes = self.env['ir.actions.report']._render_qweb_pdf(report_xmlid, [], data=datos)[0]
            pdf_parts.append(pdf_bytes)

        # Crear attachment vacío y lanzar generación en background para evitar timeouts
        fname = f"Registro Experiencia 6_24 {self.mecanico_id.name if self.mecanico_id else 'unknown'}.pdf"
        attach_vals = {
            'name': fname,
            'type': 'binary',
            'datas': False,
            'mimetype': 'application/pdf',
        }
        if self.mecanico_id:
            attach_vals.update({'res_model': 'leulit.mecanico', 'res_id': self.mecanico_id.id})
        attachment = self.env['ir.attachment'].create(attach_vals)

        # preparar parámetros para el hilo
        dbname = self.env.cr.dbname
        attachment_id = attachment.id
        report_xmlid_local = report_xmlid
        pages_local = pages
        logo_local = company_icarus.logo_reports.decode() if company_icarus.logo_reports else False
        mecanico_name_local = self.mecanico_id.name if self.mecanico_id else ''
        from_date_local = self.from_date.strftime('%d/%m/%Y') if self.from_date else ''
        to_date_local = self.to_date.strftime('%d/%m/%Y') if self.to_date else ''

        def _background_generate(dbname, attachment_id, report_xmlid, pages, logo_ica, mecanico_name, from_date_s, to_date_s):
            try:
                with api.Environment.manage():
                    with oregistry(dbname).cursor() as new_cr:
                        env = api.Environment(new_cr, SUPERUSER_ID, {})
                        pdf_parts_bg = []
                        for j in range(0, len(pages), CHUNK_PAGES):
                            pages_slice_bg = pages[j:j + CHUNK_PAGES]
                            datos_bg = {
                                'logo_ica': logo_ica,
                                'mecanico': mecanico_name,
                                'pages': pages_slice_bg,
                                'from_date': from_date_s,
                                'to_date': to_date_s,
                                'total_pages': len(pages),
                            }
                            part = env['ir.actions.report']._render_qweb_pdf(report_xmlid, [], data=datos_bg)[0]
                            pdf_parts_bg.append(part)

                        if len(pdf_parts_bg) == 1:
                            merged_bg = pdf_parts_bg[0]
                        else:
                            merged_buf = env['leulit.wizard_report_experiencia'].merge_pdfs(env['leulit.wizard_report_experiencia'], pdf_parts_bg)
                            merged_bg = merged_buf.getvalue()

                        # escribir resultado en attachment
                        env['ir.attachment'].browse(attachment_id).write({'datas': base64.b64encode(merged_bg).decode('utf-8')})
                        new_cr.commit()
            except Exception:
                _logger.exception('Error generando PDF en background')

        thread = threading.Thread(target=_background_generate, args=(dbname, attachment_id, report_xmlid_local, pages_local, logo_local, mecanico_name_local, from_date_local, to_date_local))
        thread.daemon = True
        thread.start()

        # Devolver inmediatamente URL al attachment (se completará en background)
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?model=ir.attachment&field=datas&filename_field=name&download=true",
            'target': 'self',
        }
            