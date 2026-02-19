# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import timedelta

import logging
_logger = logging.getLogger(__name__)


class leulit_wizard_report_experiencia(models.TransientModel):
    _name           = "leulit.wizard_report_experiencia"
    _description    = "leulit_wizard_report_experiencia"


    mecanico_id = fields.Many2one(comodel_name='leulit.mecanico', string='Mecánico')
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')



    def print_report_experiencia(self):
        company_icarus = self.env['res.company'].search([('name','like','Icarus')])
        # items = []
        # for item in self.env['leulit.item_experiencia_mecanico'].search([('mecanico_id','=',self.mecanico_id.id),('date','>=',self.from_date),('date','<=',self.to_date)]):
        #     for items_diff_atas in item.get_data_to_report():
        #         items.append(items_diff_atas)

        # items_per_page = 8
        # total_items = len(items)
        # remaining_items = items_per_page - (total_items % items_per_page) if total_items % items_per_page != 0 else 0
        
        # empty_item = {
        #     'date': '',
        #     'location': '',
        #     'ac_type': '',
        #     'ac_comp': '',
        #     'type_maintenance': '',
        #     'privilege': '',
        #     'fot': '',
        #     'sgh': '',
        #     'ri': '',
        #     'ts': '',
        #     'mod': '',
        #     'rep': '',
        #     'insp': '',
        #     'training': '',
        #     'perform': '',
        #     'supervise': '',
        #     'crs': '',
        #     'ata_ids': '',
        #     'operation_performed': '',
        #     'duration': '',
        #     'maintenance_record_ref': '',
        #     'remarks': '',
        # }
        
        # items.extend([empty_item.copy() for _ in range(remaining_items)])
        # pages = [items[i:i + items_per_page] for i in range(0, len(items), items_per_page)]
        items = self.env['leulit.item_experiencia_mecanico'].search([('mecanico_id','=',self.mecanico_id.id),('date','>=',self.from_date),('date','<=',self.to_date)])
        datos = {
            'logo_ica': company_icarus.logo_reports,
            'mecanico': self.mecanico_id.name if self.mecanico_id else '',
            # 'pages': pages,
            'from_date': self.from_date.strftime('%d/%m/%Y') if self.from_date else '',
            'to_date': self.to_date.strftime('%d/%m/%Y') if self.to_date else '',
            # 'total_pages': len(pages)
        }
        _logger.error('Datos para el reporte: %s', datos)
        _logger.error('Items para el reporte: %s', items)
        return {
            'type': 'ir.actions.report',
            'report_name': 'leulit_actividad_taller.leulit_20240521_1012_informe',
            'report_type': 'qweb-pdf',
            'model': 'leulit.item_experiencia_mecanico',
            'res_ids': items.ids,
            'context': self.env.context,
            'data': datos,
        }