# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceFormOne(models.Model):
    _name = "leulit.maintenance_form_one"
    _rec_name = "tracking_number"
    _order = "fecha desc"
    _inherit = ['mail.thread']


    @api.onchange('fecha')
    def _onchange_fecha(self):
        form_one_today = self.env['leulit.maintenance_form_one'].search([('fecha','=',self.fecha)])
        sequence = 1
        if len(form_one_today) > 0:
            sequence = len(form_one_today)+1
        self.tracking_number = 'ICM-'+self.fecha.strftime("%y%m%d")+'-'+str(sequence)

    def _get_status_work(self):
        return (
            ('overhauled','Overhauled'),
            ('repaired','Repaired'),
            ('inspected_tested','Inspected / Tested'),
            ('modified','Modified')
        )
        
    @api.depends('status_work')
    def _get_desc_status_work(self):
        lista = self._get_status_work()
        for item in self:
            matching = [s for s in lista if item.status_work in s]
            item.desc_status_work = matching[0][1]

    @api.onchange('task_id')
    def onchange_task_id(self):
        if self.task_id:
            text = ''
            for manual in self.task_id.manuales_ids:
                text += ' Manual:('
                if manual.name:
                    text += ' Name:<b>' + manual.name + '</b>'
                if manual.descripcion:
                    text += ' <b>' +  manual.descripcion + '</b>'
                if manual.pn:
                    text += ' PN:<b>' +  manual.pn + '</b>'
                if manual.rev_n:
                    text += ' Rev nº:<b>' +  manual.rev_n + '</b>'
                if manual.rev:
                    text += ' Rev date:<b>' +  manual.rev.strftime('%d/%m/%Y') + '</b>'
                text += ')'
            self.remarks = '{0}<br/>All aplicable AD and SB complied with'.format(text)

    @api.constrains('remarks')
    def _check_remarks_lines(self):
        MAX_LINES = 7
        for record in self:
            _logger.error('REMARKS: %s', record.remarks)
            if record.remarks:
                # Contar etiquetas <p>
                num_lines = len(re.findall(r'<p[^>]*>', record.remarks))
                # Si no hay etiquetas <p>, contar <br> + 1
                if num_lines == 0:
                    num_lines = record.remarks.count('<br') + 1
                
                if num_lines > MAX_LINES:
                    raise ValidationError(f'El campo Remarks no puede tener más de {MAX_LINES} líneas.')

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.template_id:
            self.remarks = self.template_id.remarks
        else:
            self.remarks = ''

    tracking_number = fields.Char(string="Form Tracking Number")
    work_order_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order")
    task_id = fields.Many2one(comodel_name="project.task", domain="[('maintenance_request_id','=',work_order_id)]", string="Tarea")
    items_ids = fields.One2many(comodel_name="leulit.rel_formone_lot", inverse_name="form_one", string="Items", ondelete="cascade")
    remarks = fields.Text(string="Remarks", default="")
    certificador = fields.Many2one(comodel_name="leulit.mecanico", string="Certificator")
    fecha = fields.Date(string="Date")
    part_45 = fields.Boolean(string="Part-145.A.50 Release to Service")
    other_regulation = fields.Boolean(string="Other regulation specified in block 12")
    estado = fields.Selection([('borrador', 'Borrador'),('pendiente', 'Pendiente Firma'),('firmado','Firmado')], string='Estado', default="borrador")
    status_work = fields.Selection(selection=_get_status_work, string="Status work")
    desc_status_work = fields.Char(compute=_get_desc_status_work,string='Descripción Status Work')
    boroscopia_id = fields.Many2one(comodel_name="leulit.maintenance_boroscopia", string="Boroscopia")
    template_id = fields.Many2one(comodel_name="leulit.maintenance_form_one_template", string="Plantilla Remarks")

    def wizard_send_email(self):
        context = self.env.context.copy()
        context.update({'subject': u' Se ha firmado el Form One ({0})'.format(self.tracking_number)})
        emails=['erpanomalias@helipistas.com', 'otecnica@helipistas.com']
        for emailto in emails:
            context.update({'mail_to': emailto})
            template = self.with_context(context).env.ref("leulit_taller.leulit_mail_camo_formone_firmado")
            try:
                template.send_mail(self.id, force_send=True, raise_exception=True)
            except Exception as e:
                pass

    def set_estado_borrador(self):
        self.estado = 'borrador'

    def set_estado_firmado(self):
        self.estado = 'firmado'

    def set_estado_pendiente_firma(self):
        self.estado = 'pendiente'

    def comprobar_estado_wo_form_one(self, request):
        """Comprueba si existen Form One sin firmar de la orden de trabajo"""
        for item in self.search([('work_order_id','=',request)]):
            if item.estado != 'firmado':
                raise UserError('No puede cerrar esta Orden de Trabajo porque tiene un/os Form One sin firmar.')
        return True

    def edit_form_one(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230706_1118_form')
        view_id = view_ref and view_ref[1] or False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Form One',
            'res_model': 'leulit.maintenance_form_one',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': view_id,
            'target': 'current',
        }

    def print_form_one(self):
        data = self._get_data_to_print_form_one()
        return self.env.ref('leulit_taller.leulit_20230706_1118_report').report_action(self, data=data)

    def _get_data_to_print_form_one(self):
        formonelist = []
        hashcode_interno = ''
        company_145 = self.env['res.company'].search([('name','like','Icarus')])
        for item in self:
            items_list = []
            for item_id in item.items_ids:
                item_dict = {
                    'item': item_id.item,
                    'descripcion_pieza': item_id.descripcion_pieza,
                    'pn': item_id.pn,
                    'sn': item_id.sn,
                    'qty': item_id.qty,
                    'status_work': item.desc_status_work,
                }
                items_list.append(item_dict)
            formone = {
                'tracking_number': item.tracking_number,
                'work_order_id': item.work_order_id.name if self.work_order_id else "",
                'items': items_list,
                'remarks': item.remarks,
                'part_45': item.part_45,
                'other_regulation': item.other_regulation,
                'certificador': item.certificador.name if item.certificador else "",
                'firma': item.certificador.firma if item.certificador else False,
                'sello': item.certificador.sello if item.certificador else False,
                'fecha': item.fecha.strftime("%d/%m/%Y"),
                'items_len': len(items_list),
                }
            docref = datetime.now().strftime("%Y%m%d")
            hashcode_interno = utilitylib.getHashOfData(docref)
            formonelist.append(formone)
        data = {
            'formonelist' : formonelist,
            'watermark' : company_145.watermark.decode() if company_145.watermark else False,
            'logo' : company_145.logo_reports if company_145.logo_reports else False,
            'num_pages' : len(formonelist),
            'hashcode_interno' : hashcode_interno,
            'hashcode' : False,
            'firmado_por' : False,
        }
        return data