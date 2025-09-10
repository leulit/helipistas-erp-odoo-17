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


class leulit_vuelo(models.Model):
    _name = "leulit.vuelo"
    _inherit = "leulit.vuelo"


    def buildPOVPdf(self, esignature, hack_firmado_por, hack_estado):
        for item in self:
            if hack_firmado_por == False:
                supervisor = False
                if item.piloto_supervisor_id:
                    pilotoPartner = item.piloto_supervisor_id.getPartnerId()
                    users = self.env['res.users'].get_user_by_partner(pilotoPartner)
                    uidEnv = self.env.uid
                    for user in users:
                        if user.id == uidEnv:
                            supervisor = True

                if supervisor:
                    firmado_por = item.piloto_supervisor_id.name
                    firmado_por_id = item.piloto_supervisor_id.id
                else:
                    firmado_por = item.piloto_id.name
                    firmado_por_id = item.piloto_id.id
            else:
                firmado_por = self.env['leulit.piloto'].search([('id','=',hack_firmado_por)])[0].name
                firmado_por_id = hack_firmado_por
            datos = {
                'modelo': 'leulit.vuelo',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fechavuelo,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,        
                'hack_estado' : hack_estado
            }
            referencia ="{0}-{1}-POV".format(item.id, item.estado)
            datos.update({'referencia': referencia})
            datos.update({'prefijo_hashcode': "POV"})
            datos.update({'informe': "leulit_ficha_vuelo_report"})

            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.vuelo', item.id, "POV-{0}".format(esignature))

            datos.update({'hashcode': hashcode})
            datos.update({'firmado_por': firmado_por})
            report = item.pdf_vuelo_print_report(datos)
            datos.update({'report': report}) 
            datos.update({'filename': "{0}-{1}-POV.pdf".format(item.codigo, item.estado)}) 
            return datos

    def buildPTVPdf(self, esignature, hack_firmado_por, hack_estado):
        for item in self:
            hashdata = utilitylib.getHashOfData(item)
            if hack_firmado_por == False:
                supervisor = False
                if item.piloto_supervisor_id:
                    pilotoPartner = item.piloto_supervisor_id.getPartnerId()
                    users = self.env['res.users'].get_user_by_partner(pilotoPartner)
                    uidEnv = self.env.uid
                    for user in users:
                        if user.id == uidEnv:
                            supervisor = True

                if supervisor:
                    firmado_por = item.piloto_supervisor_id.name
                    firmado_por_id = item.piloto_supervisor_id.id
                else:
                    firmado_por = item.piloto_id.name
                    firmado_por_id = item.piloto_id.id
            else:
                firmado_por = self.env['leulit.piloto'].search([('id','=',hack_firmado_por)])[0].name
                firmado_por_id = hack_firmado_por
            datos = {
                'modelo': 'leulit.vuelo',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fechavuelo,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,        
                'hack_estado' : hack_estado
            }
            #PARTE TÉCNICO DE VUELO
            referencia ="{0}-{1}-PTV".format(item.id, item.estado)
            datos.update({'referencia': referencia})
            datos.update({'prefijo_hashcode': "PTV"})
            datos.update({'informe': "hlp_20190709_1846_report"})
            datos.update({'fecha':item['fechavuelo']})
            datos.update({'helicoptero_id':item.helicoptero_id.id})
            
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.vuelo', item.id, "PTV-{0}".format(esignature))
            datos.update({'hashcode': hashcode})
            datos.update({'firmado_por': firmado_por})
            report = item.pdf_parte_vuelo_print(datos)
            datos.update({'report': report})
            datos.update({'filename': "{0}-{1}-PTV.pdf".format(item.codigo, item.estado)}) 
            return datos

    def buildF27Pdf(self, esignature, hack_firmado_por, hack_estado):
        for item in self:
            hashdata = utilitylib.getHashOfData(item)
            if hack_firmado_por == False:
                supervisor = False
                if item.piloto_supervisor_id:
                    pilotoPartner = item.piloto_supervisor_id.getPartnerId()
                    users = self.env['res.users'].get_user_by_partner(pilotoPartner)
                    uidEnv = self.env.uid
                    for user in users:
                        if user.id == uidEnv:
                            supervisor = True

                if supervisor:
                    firmado_por = item.piloto_supervisor_id.name
                    firma = item.piloto_supervisor_id.firma
                    firmado_por_id = item.piloto_supervisor_id.id
                else:
                    firmado_por = item.piloto_id.name
                    firma = item.piloto_id.firma
                    firmado_por_id = item.piloto_id.id
            else:
                piloto = self.env['leulit.piloto'].search([('id','=',hack_firmado_por)])[0]
                firmado_por = piloto.name
                firma = piloto.firma
                firmado_por_id = hack_firmado_por
            datos = {
                'modelo': 'leulit.vuelo',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : esignature,
                'fecha_firma': item.fechavuelo,
                'hack_firmado_por' : firmado_por,
                'hack_firmado_por_id' : firmado_por_id,        
                'hack_estado' : hack_estado
            }
            #PARTE TÉCNICO DE VUELO
            referencia = "{0}-F27-E4R9".format(item.id)
            datos.update({'referencia': referencia})
            datos.update({'prefijo_hashcode': "F27-E4R9"})
            datos.update({'informe': "leulit_20250507_1537_report"})
            datos.update({'fecha':item['fechavuelo']})
            datos.update({'helicoptero_id':item.helicoptero_id.id})
            
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.vuelo', item.id, "F27-E4R9-{0}".format(esignature))
            datos.update({'hashcode': hashcode})
            datos.update({'firmado_por': firmado_por})
            datos.update({'firma': firma})
            report = item.pdf_report_F27_print(datos)
            datos.update({'report': report})
            datos.update({'filename': "{0}-F27-E4R9.pdf".format(item.codigo)}) 
            return datos


    def buildFirmarDocsOdoo(self, esignature, hack_firmado_por, hack_estado):
        for item in self:
            datosPOV = self.buildPOVPdf( esignature, hack_firmado_por, hack_estado )
            datosPTV = self.buildPTVPdf( esignature, hack_firmado_por, hack_estado )
            referencia = self.getReferenciaSignature("POV", hack_estado)
            self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.vuelo', item.codigo, referencia, item.fechavuelo)
            for item2 in self.env['leulit_signaturedoc'].search([('referencia', '=', referencia)]):
                attach_id = self.env['ir.attachment'].create({
                    'name': datosPOV['filename'],
                    'type': 'binary',
                    'datas': datosPOV['report'],
                    'res_model': "leulit_signaturedoc",
                    'res_id': item2.id,
                    'public': True
                })
                datosdb = {
                    'attachment_id' : attach_id,
                    'estado' : item2.COMPLETADO,
                    'hashcode' : datosPOV['hashcode'],
                    'esignature' : datosPOV['esignature'],
                }
                item2.write(datosdb)
            
            referencia = self.getReferenciaSignature("PTV", hack_estado)
            self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.vuelo', item.codigo, referencia, item.fechavuelo)
            for item2 in self.env['leulit_signaturedoc'].search([('referencia', '=', referencia)]):
                attach_id = self.env['ir.attachment'].create({
                    'name': datosPTV['filename'],
                    'type': 'binary',
                    'datas': datosPTV['report'],
                    'res_model': "leulit_signaturedoc",
                    'res_id': item2.id,
                    'public': True
                })
                datosdb = {
                    'attachment_id' : attach_id,
                    'estado' : item2.COMPLETADO,
                    'hashcode' : datosPTV['hashcode'],
                    'esignature' : datosPTV['esignature'],
                }
                item2.write(datosdb)

            if item.helicoptero_tipo == 'EC120B' and item.checklist_prevuelo_BFF == True and item.estado == 'postvuelo':
                datosF27 = self.buildF27Pdf( esignature, hack_firmado_por, hack_estado )
                referencia = "{0}-F27-E4R9".format(item.id)
                self.env['leulit_signaturedoc'].prepareSignature(item.id, 'leulit.vuelo', item.codigo, referencia, item.fechavuelo)
                for item2 in self.env['leulit_signaturedoc'].search([('referencia', '=', referencia)]):
                    attach_id = self.env['ir.attachment'].create({
                        'name': datosF27['filename'],
                        'type': 'binary',
                        'datas': datosF27['report'],
                        'res_model': "leulit_signaturedoc",
                        'res_id': item2.id,
                        'public': True
                    })
                    datosdb = {
                        'attachment_id' : attach_id,
                        'estado' : item2.COMPLETADO,
                        'hashcode' : datosF27['hashcode'],
                        'esignature' : datosF27['esignature'],
                    }
                    item2.write(datosdb)
                
            

    def getReferenciaSignature(self, prefijo, hack_estado):
        for item in self:
            estado = item.estado
            if hack_estado:
                estado = hack_estado            
            referencia ="{0}-{1}-{2}".format(item.id, estado, prefijo)
            return referencia


    def getReferenciaSignatureF27(self, prefijo):
        for item in self:         
            referencia ="{0}-{1}".format(item.id, prefijo)
            return referencia


    def buildPdfSigned(self, datos, esignature):
        for item in self:
            estado = item.estado
            control_firma = 'firmado'
            if item.estado == 'prevuelo':
                estado = 'postvuelo'
                control_firma = 'no-firmado'
            if item.estado == 'postvuelo':
                estado = 'cerrado'
                item.update_pf_acciones()
                if item.parte_escuela_id:
                    if item.parte_escuela_id.estado == 'pendiente':
                        _logger.error('############ parte_escuela_id {}'.format(item.parte_escuela_id))
                        item.parte_escuela_id.actualizacion_parte_escuela_teoricos_practicos(item.fechavuelo, item.horasalida, item.tiemposervicio, item.alumno, item.verificado, False, item.comentario_escuela, item.valoracion_escuela)
            item.write({
                'estado' : estado,
                'control_firma' : control_firma,
            })
            item.buildFirmarDocsOdoo(esignature, False, None)


    def hackBuildPdfSigned(self, datos, esignature):
        for item in self:
            item.buildFirmarDocsOdoo(esignature, False, 'postvuelo')
            item.buildFirmarDocsOdoo(esignature, False, 'cerrado')
            item.write({
                'control_firma' : 'firmado',
            })


    def prepareSignature(self, descripcion, referencia, modelo, idmodelo, fecha_firma ):
        return self.env['leulit_signaturedoc'].prepareSignature( idmodelo, modelo, descripcion, referencia, fecha_firma )


    def _esignature_docs(self):
        for item in self:
            docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.vuelo'),('idmodelo','=',item.id)])
            if len(docs) > 0:
                self.esignature_docs = docs.ids
            else:
                self.esignature_docs = None


    def check_item_signed(self, cr, uid, ids, checkval, context={}):
        if isinstance(ids,list):
            ids = ids[0]
        item = self.pool['leulit_signaturedoc'].pendienteFirma(cr, uid, 'leulit.vuelo', ids)
        otp = ""
        pendiente = False
        if item:
            otp = item['otp']
            pendiente = True
        return {
            'otp': otp,
            'pendiente': pendiente
        }

    def generarPdfFirmado(self, idModelo, fecha_firma, firma):
        datos = self.buildPOVPdf(None, False)
        self.env['leulit_signaturedoc'].notchecksignature(datos, datos['referencia'])
        povdat = {
            'pdf' : datos['report'],
            'hashcode' : datos['hashcode']
        }
                
        datos = self.buildPTVPdf(None, False)
        self.env['leulit_signaturedoc'].notchecksignature(datos, datos['referencia'])        
        ptvdat =  {
            'pdf' : datos['report'],
            'hashcode' : datos['hashcode']
        }        
        return [povdat,ptvdat]
      
    def _semaforo_firma(self):
        for item in self:
            item.semaforo_firma = "N.A."
            if item.estado in ['cerrado','postvuelo']:
                if item.fechavuelo >= datetime(2022, 2, 1).date():
                    valor = 'red'
                    if item.control_firma == 'firmado':
                        valor = 'green'
                    item.semaforo_firma = valor

    def verificar_actividad_aerea(self, fecha, partner):
        o_aa = self.env['leulit.actividad_aerea']
        o_vul = self.env['leulit.vuelo']

        _logger.error('############# verificar_actividad_aerea  -->  fecha %r',fecha)
        _logger.error('############# verificar_actividad_aerea  -->  partner %r',partner)
        vuls = o_vul.search([('estado','=','cerrado'),('fechavuelo','=',fecha),'|','|','|',('piloto_id','=',partner.getPiloto()),('operador','=',partner.getOperador()),('verificado','=',partner.getPiloto()),('alumno','=',partner.getAlumno())], order="fechavuelo ASC, horasalida ASC")
        _logger.error('############# verificar_actividad_aerea  -->  vuls %r',vuls)
        if vuls:
            items_vul = o_vul.search(['|',('id','in',vuls.ids),('id','=',self.id)])
        else:
            items_vul = o_vul.search([('id','=',self.id)])
        _logger.error('############# verificar_actividad_aerea  -->  vuls %r',vuls)
        max_duracion = 0.0
        tiempo_desc_parcial = 0.0
        tiempo_amplia = 0.0
        inicioitems = 1111.0
        finitems = 0.0
        incremento = 0.0
        airtime = 0.0
        tiempo_vuelo = 0.0
        for index,itemvul in enumerate(items_vul):
            airtime += itemvul.airtime
            tiempo_vuelo += itemvul.tiemposervicio

            #cálculo tiempo máxima de actividad
            if itemvul.tipo_actividad in o_aa.tiempo_maximo_tipo_actividad:
                max_duracion = max(o_aa.tiempo_maximo_tipo_actividad[ itemvul.tipo_actividad ], max_duracion)
            else:
                if itemvul.parte_escuela_id:
                    if itemvul.parte_escuela_id.isvueloato(itemvul.id):
                        max_duracion = o_aa.tiempo_maximo_tipo_actividad['Escuela-ATO']
                    else:
                        max_duracion = o_aa.tiempo_maximo_tipo_actividad['Escuela-noATO']
                else:
                    max_duracion = o_aa.default_tiempo_maximo_tipo_actividad
            #cálculos descanso parcial
            if (index > 0):
                itemaaAnt = items_vul[index-1]
                intervalo = round(float(itemvul.horasalida),2) - round(float(itemaaAnt.horallegada),2)
                if intervalo >= o_aa.descanso_parcial_min and intervalo <= o_aa.descanso_parcial_max:
                    if intervalo > o_aa.descanso_parcial_max:
                        intervalo = 8.0
                    incremento = round((intervalo / 2.0),2)
                
                    tiempo_desc_parcial = tiempo_desc_parcial + intervalo
                    tiempo_amplia = tiempo_amplia + incremento

            inicioitems = min(inicioitems, itemvul.horasalida)
            finitems = max(finitems, itemvul.horallegada)
        
        _logger.error('############# verificar_actividad_aerea  -->  max_duracion %r',max_duracion)
        _logger.error('############# verificar_actividad_aerea  -->  tiempo_amplia %r',tiempo_amplia)
        _logger.error('############# verificar_actividad_aerea  -->  finitems %r',finitems)
        _logger.error('############# verificar_actividad_aerea  -->  inicioitems %r',inicioitems)
        _logger.error('############# verificar_actividad_aerea  -->  (max_duracion + tiempo_amplia) >= (finitems - inicioitems)')
        _logger.error('############# verificar_actividad_aerea  -->  %r + %r = %r',max_duracion, tiempo_amplia, (max_duracion + tiempo_amplia))
        _logger.error('############# verificar_actividad_aerea  -->  %r - %r = %r',finitems, inicioitems, (finitems - inicioitems))
        _logger.error('############# verificar_actividad_aerea  -->  %r >= %r',(max_duracion + tiempo_amplia), (finitems - inicioitems))

        if (max_duracion + tiempo_amplia) >= (finitems - inicioitems):
            _logger.error('############# verificar_actividad_aerea  --> True (Esta dentro del tiempo maximo de actividad)')
            return True
        
        _logger.error('############# verificar_actividad_aerea  --> False (Se pasa del tiempo maximo de actividad)')
        return False

    def firmar_doc_parte_vuelo(self):
        if self.estado == 'postvuelo':
            self.wkf_act_cerrado()
            full_actividad_aerea = False
            who = False
            # si verificar_actividad_aerea devuelve TRUE se puede acabar de firmar el parte, si devuelve FALSE pasa el tiempo de actividad aerea, y se debera gestionar una ocurrencia.
            if self.piloto_id:
                partner = self.env['res.partner'].search([('id','=',self.piloto_id.getPartnerId())])
                if partner:
                    if not self.verificar_actividad_aerea(self.fechavuelo, partner):
                        full_actividad_aerea = True
                        who = partner
            if self.operador:
                partner = self.env['res.partner'].search([('id','=',self.operador.getPartnerId())])
                if partner:
                    if not self.verificar_actividad_aerea(self.fechavuelo, partner):
                        full_actividad_aerea = True
                        who = partner
            if self.alumno:
                partner = self.env['res.partner'].search([('id','=',self.alumno.getPartnerId())])
                if partner:
                    if not self.verificar_actividad_aerea(self.fechavuelo, partner):
                        full_actividad_aerea = True
                        who = partner
            if self.verificado:
                partner = self.env['res.partner'].search([('id','=',self.verificado.getPartnerId())])
                if partner:
                    if not self.verificar_actividad_aerea(self.fechavuelo, partner):
                        full_actividad_aerea = True
                        who = partner

            if full_actividad_aerea:
                raise UserError(_("No se puede firmar el parte de vuelo porque se ha excedido el tiempo máximo de actividad aérea. Debe crear una ocurrencia para gestionar el exceso de tiempo de actividad aérea."))
                # view_ref = self.env['ir.model.data'].get_object_reference('leulit_esignature','leulit_202306071553_form')
                # view_id = view_ref and view_ref[1] or False
                # return {
                #     'type': 'ir.actions.act_window',
                #     'name': 'Crear Ocurrencia',
                #     'res_model': 'wizard_create_claim_from_vuelo',
                #     'view_mode': 'form',
                #     'view_id': view_id,
                #     'target': 'new',
                #     'context': {'default_vuelo': self.id, 'default_who':who.id}
                # }
        if self.estado == 'prevuelo':
            if self.env['res.users'].get_piloto_freelance() and len(self.env['leulit.freelance_actividad_aerea'].search([('user','=',self.env.uid),('date','=',self.fechavuelo)])) == 0:
                view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones', 'leulit_20250320_1123_form')
                view_id = view_ref and view_ref[1] or False
                context = {
                    'default_date' : self.fechavuelo,
                }
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Actividad Aerea',
                    'res_model': 'leulit.wizard_freelance_actividad_aerea',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'new',
                    'context': context
                }
            self.wkf_act_postvuelo()
        self.write({'control_firma' : 'pendiente'})

    def get_partner_vuelo(self, vuelo_id, tripulante):
        """
        Obtiene el partner asociado a un tripulante de un vuelo.
        :param vuelo_id: ID del vuelo.
        :param tripulante: Tipo de tripulante ('piloto', 'operador', 'alumno', 'verificado').
        """
        vuelo = self.search([('id','=',vuelo_id)])
        if tripulante == 'piloto':
            _logger.error('############# get_partner_vuelo   -->  piloto %r',vuelo.piloto_id.getPartnerId())
        elif tripulante == 'operador':
            _logger.error('############# get_partner_vuelo   -->  operador %r',vuelo.operador.getPartnerId())
        elif tripulante == 'alumno':
            _logger.error('############# get_partner_vuelo   -->  alumno %r',vuelo.alumno.getPartnerId())
        elif tripulante == 'verificado':
            _logger.error('############# get_partner_vuelo   -->  verificado %r',vuelo.verificado.getPartnerId())


    def wizard_cancelar(self):
        super(leulit_vuelo, self).wizard_cancelar()
        if self.control_firma == 'pendiente':
            self.control_firma = 'no-firmado'

    def _can_sign(self):
        for item in self:
            item.can_sign = False
            vuelos = self.env['leulit.vuelo'].search([('control_firma','=','pendiente'),'|',('helicoptero_id','=',item.helicoptero_id.id),('piloto_id','=',item.piloto_id.id)])
            if len(vuelos) == 0:
                if item.estado == 'prevuelo' and item.control_firma == 'no-firmado':
                    item.can_sign = True
            if item.estado == 'postvuelo' and item.control_firma == 'no-firmado':
                item.can_sign = True
            if item.estado == 'cerrado' and item.control_firma == 'pendiente':
                item.can_sign = True

    def wizardSetPrevuelo(self):
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.vuelo'),('idmodelo','=',self.id)])
        docs.unlink()
        self.control_firma = 'no-firmado'
        return super(leulit_vuelo, self).wizardSetPrevuelo()


    esignature_docs = fields.One2many(compute=_esignature_docs, comodel_name='leulit_signaturedoc', string='Docs firmados', store=False)
    semaforo_firma = fields.Char(compute=_semaforo_firma, store=False, string='Semáforo')
    control_firma = fields.Selection([('no-firmado','No firmado'),('pendiente','Pendiente'),('firmado','Firmado')], 'Estado firma', default="no-firmado")
    can_sign = fields.Boolean(compute=_can_sign, store=False)
    verificado_postvuelo = fields.Boolean('Checks postvuelo',default=False)

    def getAllPendientesFirma(self):
        items = self.env['leulit.vuelo'].search([('control_firma','in',['pendiente']),('estado','in',['prevuelo','postvuelo']),('fechavuelo','>','2022-02-22')], order= "fechavuelo DESC")
        return items
