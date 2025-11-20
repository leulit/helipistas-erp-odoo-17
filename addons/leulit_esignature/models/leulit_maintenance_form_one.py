# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
import base64
import threading
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceFormOne(models.Model):
    _name = "leulit.maintenance_form_one"
    _inherit = 'leulit.maintenance_form_one'


    def _esignature_docs(self):
        for item in self:
            docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_form_one'),('idmodelo','=',item.id)])
            if len(docs) > 0:
                item.esignature_docs = docs.ids
            else:
                item.esignature_docs = False
                

    esignature_docs = fields.One2many(compute=_esignature_docs, comodel_name='leulit_signaturedoc', string='Documentos firma', store=False)


    def set_estado_borrador(self):
        super(LeulitMaintenanceFormOne, self).set_estado_borrador()
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_form_one'),('idmodelo','=',self.id)])
        docs.unlink()
    
    def getAllPendientesFirma(self):
        items = []
        if self.env.user.can_sign_formone:
            for item in self.search([('estado','=','pendiente')], order= "fecha DESC"):
                items.append(item)
        return items

    def buildPdfSigned(self, datos, esignature):
        _logger.error('##############################    buildPdfSigned   -->  firmando form one')
        for item in self:
            item.buildFirmarDocsOdoo(esignature, False)
            item.set_estado_firmado()

    def buildFirmarDocsOdoo(self, esignature, hack_firmado_por):
        _logger.error('##############################    buildFirmarDocsOdoo   -->  firmando form one')
        for item in self:
            referencia = item.tracking_number
            self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.maintenance_form_one', item.tracking_number, referencia, item.fecha)
            
            datospdf = self.generarPdfFirmado( esignature, hack_firmado_por )
            for item2 in self.env['leulit_signaturedoc'].search([('referencia', '=', referencia)]):
                attach_id = self.env['ir.attachment'].create({
                    'name': datospdf['filename'],
                    'type': 'binary',
                    'datas': datospdf['report'],
                    'res_model': "leulit_signaturedoc",
                    'res_id': item2.id,
                    'public': True
                })
                datosdb = {
                    'attachment_id' : attach_id,
                    'estado' : item2.COMPLETADO,
                    'hashcode' : datospdf['hashcode'],
                    'esignature' : datospdf['esignature'],
                }
                item2.write(datosdb)

    def generarPdfFirmado(self, esignature, hack_firmado_por):
        for item in self:
            _logger.error('##############################    generarPdfFirmado   -->  firmando form one')
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.maintenance_form_one', item.id, item.tracking_number)
            if hack_firmado_por == False:
                firmado_por = self.env.user.name
                firmado_por_id = self.env.user.id
            else:
                firmado_por = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].name
                firmado_por_id = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].id

            datos = {
                'modelo': 'leulit.maintenance_form_one',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fecha,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,
                'hashcode' : hashcode,
                'referencia': item.tracking_number,
                'filename': '{0}.pdf'.format(item.tracking_number),
                'prefijo_hashcode': "ICM",
            }

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
                        'status_work': item.status_work,
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
                    'sello': item.certificador.sello,
                    'fecha': item.fecha.strftime("%d/%m/%Y"),
                    }
                docref = datetime.now().strftime("%Y%m%d")
                hashcode_interno = utilitylib.getHashOfData(docref)
                formonelist.append(formone)
            data = {
                'formonelist' : formonelist,
                'watermark' : company_145.watermark.decode() if company_145.watermark else False,
                'logo' : company_145.logo_reports.decode() if company_145.logo_reports else False,
                'num_pages' : len(formonelist),
                'hashcode_interno' : False,
                'hashcode' : hashcode,
                'firmado_por' : firmado_por,
            }
            report = self.env.ref('leulit_taller.leulit_20230706_1118_report')
            pdf = self.env['ir.actions.report']._render_qweb_pdf(report,[],data=data)[0]
            report = base64.b64encode(pdf)
            datos.update({'report': report})
            return datos


    def firmar_formones(self, fecha):
        _logger.error("################### firmar_formones ")
        threaded_calculation = threading.Thread(target=self.run_firmar_formones, args=([fecha]))
        _logger.error("################### firmar_formones start thread")
        threaded_calculation.start()

    def run_firmar_formones(self, fecha):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            formones = self.env['leulit.maintenance_form_one'].with_context(context).sudo().search([('fecha','>=',fecha), ('estado', '=', 'firmado')])
            for formone in formones:
                formone.esignature_docs.unlink()
                args={'otp':'123456',
                      'notp':'123456',
                      'modelo':'leulit.maintenance_form_one',
                      'idmodelo':formone.id}
                context['args']=args
                user = False
                if formone.certificador:
                    user = self.env['res.users'].with_context(context).sudo().search([('partner_id','=',formone.certificador.getPartnerId())])

                self.env.uid = user.id if user else 14
                self.env['leulit_signaturedoc'].with_context(context).sudo().checksignatureRef()
                self.env.cr.commit()
        _logger.error('################### firmar_formones fin thread')
