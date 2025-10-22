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


class Anomalia(models.Model):
    _inherit = 'leulit.anomalia'

    def getAllPendientesFirma(self):
        items = []
        if self.env.user.can_sign_anomalia:
            for item in self.env['leulit.anomalia'].search([('fecha','>=','2020-09-11'),('check_firmado','=',False),('estado','not in',['pending','edicion'])], order= "fecha DESC"):
                items.append(item)
            # for item in self.env['leulit.anomalia'].search([('fecha','>=','2020-09-11')], order= "fecha DESC"):
            #     if item.semaforo_firma == 'red':
            #         items.append(item)
        return items


    def prepareSignature(self, descripcion, referencia, modelo, idmodelo, fecha_firma):
        return self.env['leulit_signaturedoc'].prepareSignature( idmodelo, modelo, descripcion, referencia, fecha_firma)


    def buildFirmarDocsOdoo(self, esignature, hack_firmado_por):
        _logger.error('##############################    buildFirmarDocsOdoo   -->  firmando anomalia')
        for item in self:
            referencia = 'ANO-[{0}]-{1}'.format(item.id, item.estado)
            self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.anomalia', item.codigo, referencia, item.fecha)


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


    def buildPdfSigned(self, datos, esignature):
        _logger.error('##############################    buildPdfSigned   -->  firmando anomalia')
        for item in self:
            item.buildFirmarDocsOdoo(esignature, False)
            item.check_firmado = True


    def generarPdfFirmado(self, esignature, hack_firmado_por):
        for item in self:
            _logger.error('##############################    generarPdfFirmado   -->  firmando anomalia')
            company_helipistas = self.env['res.company'].search([('name','like','Helipistas')])
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.anomalia', item.id, "ANO-{0}".format(esignature))
            if hack_firmado_por == False:
                firmado_por = self.env.user.name
                firmado_por_id = self.env.user.id
            else:
                firmado_por = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].name
                firmado_por_id = self.env['res.users'].search([('id','=',hack_firmado_por)])[0].id

            datos = {
                'modelo': 'leulit.anomalia',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fecha_accion,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,
                'hashcode' : hashcode,
                'referencia': 'ANO-[{0}]-{1}'.format(item.id, item.estado),
                'filename': 'ANO-[{0}]-{1}.pdf'.format(item.id, item.estado),
                'prefijo_hashcode': "ANO",
            }
            rol_informa = ''
            rol_difiere = ''
            rol_close = ''
            if item.rol_informa:
                rol_informa = 'Pilot' if item.rol_informa == 1 else 'Mechanic'
            if item.rol_difiere:
                rol_difiere = 'Pilot' if item.rol_difiere == 1 else 'Mechanic'
            if item.rol_close:
                rol_close = 'Pilot' if item.rol_close == 1 else 'Mechanic'

            data = {
                'fecha_firma' : item.fecha_accion,
                'codigo' : item.codigo,
                'id' : item.id,
                'melref' : item.melref.referencia if item.melref else "N/A",
                'linemel_id' : item.linemel_id.referencia if item.linemel_id else "N/A",
                'tipomel' : item.tipomel.name if item.tipomel else "N/A",
                'categoria' : item.categoria if item.categoria else "N/A",
                'numinstaladomel' : item.numinstaladomel if item.numinstaladomel else "0",
                'numexpmel' : item.numexpmel if item.numexpmel else "N/A",
                'pom' : item.pom if item.pom else "N/A",
                'limita' : item.limita,
                'tenerencuentamel' : item.tenerencuentamel if item.tenerencuentamel else "N/A",
                'fechalimite' : item.fechalimite if item.fechalimite else "N/A",
                'fechadiferido' : item.fechadiferido if item.fechadiferido else "N/A",
                'rol_informa' : rol_informa,
                'rol_difiere' : rol_difiere,
                'rol_close' : rol_close,
                'lugaranomalia' : item.lugaranomalia if item.lugaranomalia else "N/A",
                'fecha_crs' : item.fecha_crs if item.fecha_crs else "N/A",

                'discrepancia' : item.discrepancia if item.discrepancia else "N/A",
                'motivodiferir' : item.motivodiferir if item.motivodiferir else "N/A",
                'comentario' : item.comentario if item.comentario else "N/A",
                'lugar_crs' : item.lugar_crs if item.lugar_crs else "N/A",
                'comentario_crs' : item.comentario_crs if item.comentario_crs else "N/A",
                'fecha' : item.fecha if item.fecha else "N/A",

                'crs_por' : item.crs_por.name if item.crs_por else "N/A",
                'firma_crs_por' : item.firma_crs_por,
                'sello_crs_por' : item.sello_crs_por,

                'informado_por' : item.informado_por.name if item.informado_por else "N/A",
                'firma_informado_por' : item.firma_informado_por,
                'sello_informado_por' : item.sello_informado_por,

                'diferido_por' : item.diferido_por.name if item.diferido_por else "N/A",
                'firma_diferido_por' : item.firma_diferido_por,
                'sello_diferido_por' : item.sello_diferido_por,

                'cerrado_por' : item.cerrado_por.name if item.cerrado_por else "N/A",            
                'cerrado_por_company' : item.cerrado_por_company,
                'firma_cerrado_por' : item.firma_cerrado_por,
                'sello_cerrado_por' : item.sello_cerrado_por,

                'cancelado_por' : item.cancelado_por.name if item.cancelado_por else "N/A",
                'firma_cancelado_por' : item.firma_cancelado_por,
                'sello_cancelado_por' : item.sello_cancelado_por,

                'fecha_cancelado' : item.fecha_cancelado,
                'accion' : item.accion if item.accion else "N/A",
                'fecha_accion' : item.fecha_accion if item.fecha_accion else "N/A",
                'cas' : item.cas if item.cas else "N/A",

                'vuelo_id' : item.vuelo_id.codigo if item.vuelo_id else "N/A",

                'helicoptero_id' : item.helicoptero_id.name if item.helicoptero_id else "N/A",
                'baja_helicoptero' : item.baja_helicoptero,
                'fabricante' : item.fabricante,

                'airtime' : item.airtime,
                'strairtime' : item.strairtime,
                'estado' : item.estado,

                'fechavuelo' : item.fechavuelo if item.fechavuelo else "N/A",
                'lugarllegada' : item.lugarllegada.name if item.lugarllegada else "N/A",
                'lugarsalida' : item.lugarsalida.name if item.lugarsalida else "N/A",
                'horasalida' : item.horasalida if item.horasalida else "Unk.",
                'horallegada' : item.horallegada if item.horallegada else "Unk.",
                'oilqty' : item.oilqty,
                'fuelqty' : item.fuelqty,
                'consumomedio_vuelo' : item.consumomedio_vuelo,
                'fuelsalida_kg' : item.fuelsalida_kg,

                'notificacion_sms' : item.notificacion_sms if item.notificacion_sms else "N/A",
                'firmado_por' : firmado_por,
                'hashcode' : hashcode,
                'logo_hlp' : company_helipistas.logo_reports
            }
            pdf = self.env.ref('leulit_seguridad.leulit_200511_1627_imprimir_anomalia')._render_qweb_pdf([],data=data)[0]
            report = base64.encodestring(pdf)
            datos.update({'report': report})
            return datos
        
    def _get_report_base_filename(self):
        self.ensure_one()
        return 'ANOMALIA-%s' % (self.codigo)


    def _esignature_docs(self):
        for item in self:
            docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.anomalia'),('idmodelo','=',item.id)])
            if len(docs) > 0:
                item.esignature_docs = docs.ids
            else:
                item.esignature_docs = None


    def _semaforo_firma(self):
        for item in self:
            if item.fecha > datetime(2020, 9, 11).date():            
                valor = 'red'                
                docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.anomalia'),('idmodelo','=',item.id)])
                for signaturedoc in docs:
                    if signaturedoc.estado == signaturedoc.COMPLETADO:
                        valor = 'green'
                item.semaforo_firma = valor
            else:
                item.semaforo_firma = "N.A."

    
    def get_anomalias_unsigned_by_helicoptero(self, helicoptero_id):
        return self.search([('helicoptero_id','=',helicoptero_id),('check_firmado','=',False),('estado', '!=', 'edicion')])
    

    def haveNoGo(self, helicoptero_id, fecha):
        nitems = self.search_count([('fecha','<=',fecha),('helicoptero_id','=',helicoptero_id),('check_firmado','=',False),('estado', '!=', 'edicion')])
        return nitems > 0


    esignature_docs = fields.One2many(compute=_esignature_docs, comodel_name='leulit_signaturedoc', string='Documentos firma', store=False)
    semaforo_firma = fields.Char(compute=_semaforo_firma, store=False, string='Semáforo')
    check_firmado = fields.Boolean(string="Anomalia firmada", default=False)