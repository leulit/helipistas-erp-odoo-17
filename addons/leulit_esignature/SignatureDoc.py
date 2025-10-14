# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64
import io
import pyqrcode

_logger = logging.getLogger(__name__)


class SignatureDoc(models.Model):
    _name = "leulit_signaturedoc"
    _description = "leulit_signaturedoc"
    _order = "name"

    NUEVO = 'nuevo'
    VALIDADO = 'validado'
    COMPLETADO = 'completado'

    def popUpDescargaDocFirmado(self, idmodelo):
        self.ensure_one()
        view = self.env.ref('leulit_esignature.leulit_202009151825_form',raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documento firmado',
            'res_model': 'leulit_signaturedoc',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'res_id': idmodelo,
            'nodestroy': True,
            'context': {},
        }  


    #eliminar cuando se implante el campo referencia
    def pendienteFirma(self, cr, uid, modelo, idmodelo):
        import json
        if isinstance(idmodelo,list):
            idmodelo = idmodelo[0]
        ids = self.search(cr, uid, [('modelo','=',modelo),('idmodelo','=',idmodelo),('estado','=',self.NUEVO)])
        if ids and len(ids) > 0:
            if isinstance(ids, list):
                if len(ids) > 0:
                    ids = ids[0]
                else: 
                    return False
            item = self.read(cr, uid, ids, ['id','otp'])            
            notp = self.pool['res.users'].get_otp(cr,uid)
            if notp != item['otp']:
                self.write(cr, uid, ids, {'otp': notp})
                item['otp'] = notp                
            return item            
        else:
            return False


    #substituye al pendienteFirma por la aparición del campo referencia
    def pendienteFirmaRef(self, modelo, idmodelo, referencia):
        import json
        for item in self:
            if item.estado == self.NUEVO:
                notp = self.env.user.get_otp()
                if notp != item.otp:
                    return notp
                return item.otp            
        return False            

    
    def allPendienteFirma(self):
        import json
        args = self._context.get('args',[])
        params = args['params']
        modelo = params['modelo']
        items = self.search([('modelo','=',modelo),('estado','=',self.NUEVO)])
        if items and len(items) > 0:
            #notp = self.pool['res.users'].get_otp()
            notp = self.env.user.get_otp()
            jsonitems = []
            for item in items:
                item.notp = notp           
                jsonitems.append({
                    'name' : item.name,
                    'datas_fname' : item.datas_fname,
                    'esignature' : item.esignature,
                    'hashcode' : item.hashcode,
                    'modelo' : item.modelo,
                    'referencia' : item.referencia,
                    'idmodelo' : item.idmodelo,
                    'firmado_por' : item.firmado_por,
                    'fecha_create' : item.fecha_create,
                    'fecha_valid' : item.fecha_valid,
                    'estado' : item.estado,
                    'otp' : item.otp,
                    'notp' : item.notp,
                    'qrtext' : item.qrtext,
                    'firmado' : item.firmado,
                })
            return {
                'error': False,
                'docs': jsonitems,
            }
        else:
            return {
                'error': True,
                'docs': False,
            }
    

    def uidCanSign(self, item, modelo):
        uidEnv = self.env.uid        
        if modelo == 'leulit.vuelo':
            pilotoPartner = item.piloto_id.getPartnerId()
            users = self.env['res.users'].get_user_by_partner(pilotoPartner)
            for user in users:
                if user.id == uidEnv:
                    return True
            pilotoSupervisorPartner = item.piloto_supervisor_id.getPartnerId()
            users = self.env['res.users'].get_user_by_partner(pilotoSupervisorPartner)
            for user in users:
                if user.id == uidEnv:
                    return True
        else:
            if modelo == 'leulit.anomalia':
                return True
            if modelo == 'leulit.maintenance_crs':
                return True
            if modelo == 'leulit.maintenance_form_one':
                return True
            if modelo == 'leulit.maintenance_boroscopia':
                return True

        '''
        if self.env.uid == 11:
            return item.firmado_por and item.firmado_por == 343
        else:
            return uidPartner and item.firmado_por and uidPartner.id == item.firmado_por.id
        '''

    def codeFromServer(self):
        notp = self.env.user.get_otp()
        return {
            'notp': notp,
        }

    def allPendienteFirmaOdoo(self):
        import json
        args = self._context.get('args',[])
        params = args['params']
        #modelo = params['modelo']
        jsonitems = []
        notp = self.env.user.get_otp()
        items = self.env['leulit.maintenance_boroscopia'].getAllPendientesFirma()
        if items and len(items) > 0:
            for item in items:
                if self.uidCanSign(item, 'leulit.maintenance_boroscopia'):
                    jsonitems.append({
                        'name' : item.name,
                        'modelo' : 'leulit.maintenance_boroscopia',
                        'idmodelo' : item.id,
                        'estado' : '',
                        'otp' : '',
                        'notp' : notp,
                        'fecha' : item.fecha,
                        'referencia' : "",
                        'estado_modelo' : item.estado,
                    })
        items = self.env['leulit.maintenance_crs'].getAllPendientesFirma()
        if items and len(items) > 0:
            for item in items:
                if self.uidCanSign(item, 'leulit.maintenance_crs'):
                    jsonitems.append({
                        'name' : item.n_cas,
                        'modelo' : 'leulit.maintenance_crs',
                        'idmodelo' : item.id,
                        'estado' : '',
                        'otp' : '',
                        'notp' : notp,
                        'fecha' : item.fecha,
                        'referencia' : "",
                        'estado_modelo' : item.estado,
                    })
        items = self.env['leulit.maintenance_form_one'].getAllPendientesFirma()
        if items and len(items) > 0:
            for item in items:
                if self.uidCanSign(item, 'leulit.maintenance_form_one'):
                    jsonitems.append({
                        'name' : item.tracking_number,
                        'modelo' : 'leulit.maintenance_form_one',
                        'idmodelo' : item.id,
                        'estado' : '',
                        'otp' : '',
                        'notp' : notp,
                        'fecha' : item.fecha,
                        'referencia' : "",
                        'estado_modelo' : item.estado,
                    })
        items = self.env['leulit.anomalia'].getAllPendientesFirma()
        if items and len(items) > 0:
            for item in items:
                if self.uidCanSign(item, 'leulit.anomalia'):
                    jsonitems.append({
                        'name' : "{0}".format(item.codigo),
                        'modelo' : 'leulit.anomalia',
                        'idmodelo' : item.id,
                        'estado' : '',
                        'otp' : '',
                        'notp' : notp,
                        'fecha' : item.fecha,                
                        'referencia' : "",           
                        'estado_modelo' : item.estado,         
                    })
        items = self.env['leulit.vuelo'].getAllPendientesFirma()
        if items and len(items) > 0:
            for item in items:
                if self.uidCanSign(item, 'leulit.vuelo'):
                    jsonitems.append({
                        'name' : item.codigo,
                        'modelo' : 'leulit.vuelo',
                        'idmodelo' : item.id,
                        'estado' : '',
                        'otp' : '',
                        'notp' : notp,
                        'fecha' : item.fechavuelo,     
                        'referencia' : "",
                        'estado_modelo' : item.estado,
                    })                    
        jsonitems = sorted(jsonitems, key=lambda d: d['fecha'], reverse = True) 
        return {
            'error': False,
            'docs': jsonitems,
        }
   


    def crearNuevo( self, datos ):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(datos['idmodelo'],list):
            datos['idmodelo'] = datos['idmodelo'][0]
        items = self.search([('modelo','=',datos['modelo']),('idmodelo','=',datos['idmodelo']),('referencia','=',datos['referencia'])])                
        datos['estado'] = self.NUEVO
        datos['firmado_por'] = self.env.user.partner_id.id
        datos['fecha_create'] = fecha
        datos['attachment_id'] = False
        if len(items.ids) > 0:
            items.write(datos)
            return items                        
        else:
            return self.create(datos)



    def crearValidado(self, datos):
        if isinstance(datos['idmodelo'],list):
            datos['idmodelo'] = datos['idmodelo'][0]        
        for item in self.search([('modelo','=',datos['modelo']),('idmodelo','=',datos['idmodelo']),('estado','=',self.NUEVO)]):

            datosdb = {}
            datosdb['estado'] = self.VALIDADO
            datosdb['firmado_por'] = self.env.user.partner_id.id

            datosdb['modelo'] = item.modelo
            datosdb['idmodelo'] = item.idmodelo
            datosdb['id'] = item.id
            datosdb['fecha_valid'] = item.fecha_valid
            datosdb['esignature'] = item.esignature
            
            file_name = "{0}-{1}.pdf".format(datosdb['modelo'], datosdb['idmodelo'])
            attach_id = self.env['ir.attachment'].create({
                'name': file_name,
                'type': 'binary',
                'datas': datos['result'],
                'res_model': "leulit_signaturedoc",
                'res_id': datosdb['id'],
                'public' : True            
            })
            datosdb['attachment_id'] = attach_id
            datosdb['estado'] = self.COMPLETADO
            datosdb['hashcode'] = datos['hashcode']
            item.write(datosdb)
            return item.id


    #substituye al método crearValidado para utilizar el campo referencia
    def crearValidadoRef(self, datos, referencia):        
        if isinstance(datos['idmodelo'],list):
            datos['idmodelo'] = datos['idmodelo'][0]          
        for item in self:
            datosdb = {}
            datosdb['estado'] = self.VALIDADO
            datosdb['firmado_por'] = self.env.user.partner_id.id

            datosdb['modelo'] = item.modelo
            datosdb['idmodelo'] = item.idmodelo
            datosdb['id'] = item.id
            datosdb['fecha_valid'] = item.fecha_valid
            datosdb['esignature'] = item.esignature
                        
            file_name = "{0}-{1}.pdf".format(datosdb['modelo'], referencia)

            attach_id = self.env['ir.attachment'].create({
                'name': file_name,
                'type': 'binary',
                'datas': datos['report'],
                'res_model': "leulit_signaturedoc",
                'res_id': datosdb['id'],
                'public' : True
            })

            datosdb['attachment_id'] = attach_id
            datosdb['estado'] = self.COMPLETADO
            datosdb['hashcode'] = datos['hashcode']
            item.write(datosdb)
            return item.id

    def marcarComoFirmado(self,firma):   
        for item in self:   
            item.write({'firma': firma, 'estado': self.VALIDADO, 'otp_qrcode': False} )

    def buildSignature(self, modelo, idmodelo, code):
        import json
        otp_qr = {
            'modelo': modelo,
            'idmodelo': idmodelo,
            'otp': code,            
        }
        otp_qrstr = json.dumps(otp_qr)
        esignature = self.env.user.hashEncodeWithSecret(otp_qrstr)
        return esignature

    def prepareSignature(self, idmodelo, model, descripcion, referencia, fecha_firma):
        otp = self.env.user.get_otp()
        mensaje = descripcion        
        esignature = self.buildSignature(model, idmodelo, otp)
        buffer = io.BytesIO()
        qr = pyqrcode.create(esignature)
        qr.png(buffer,scale=3)    
        bufferValue = buffer.getvalue()
        binary = base64.b64encode( bufferValue )
        datos = {
            'name'   :   mensaje,
            'modelo'  :  model,
            'idmodelo' : idmodelo,
            'esignature'    : esignature,
            'otp_qrcode'    : binary,
            'otp'    :   otp,
            'qrtext'  :  esignature,
            'fecha_valid'   : fecha_firma,
            'referencia'    : referencia
        }
        iddoc = self.crearNuevo(datos)
        return iddoc    


    def notchecksignature(self, datos, referencia):    
        for item in self.search([('referencia','=',referencia)], order='fecha_create DESC'):
            if not item.pendienteFirmaRef(datos['modelo'], datos['idmodelo'], referencia): 
                return False
            else:
                item.crearValidadoRef(datos, referencia)   
                item.marcarComoFirmado(None)        
                return item.id
        else:
            return False
        

    def pruebas_checksignatureRef(self,id):
        context = dict(self._context)
        vuelo = self.env['leulit.vuelo'].search([('id','=',id)])
        args={'otp':'123456',
                      'notp':'123456',
                      'modelo':'leulit.vuelo',
                      'idmodelo':vuelo.id}
        context['args']=args
        if vuelo.piloto_supervisor_id:
            user = self.env['res.users'].with_context(context).sudo().search([('partner_id','=',vuelo.piloto_supervisor_id.partner_id.id)])
        else:    
            user = self.env['res.users'].with_context(context).sudo().search([('partner_id','=',vuelo.piloto_id.partner_id.id)])
        if user:
            self.env.uid = user.id
            self.env['leulit_signaturedoc'].with_context(context).sudo().checksignatureRef()


    def checksignatureRef(self):
        result = False
        error = False
        errMsg = ""
        datos = self._context.get('args',[])
        codigo = datos['otp']
        result = datos['otp'] ==  datos['notp']
        valid = False
        if result:
            for item in self.env[datos['modelo']].search([('id','=',datos['idmodelo'])]):
                esignature = self.buildSignature(datos['modelo'], datos['idmodelo'], codigo)
                item.buildPdfSigned(datos, esignature)
            valid = True
        resultado = {
            'valid': valid,
            'error': error,
            'errmsg': errMsg,
        }
        return resultado


    def hacksignature(self, idpersona, iddocumento, estado):
        result = False
        error = False
        errMsg = ""
        for item in self.browse(int(iddocumento)):
            result = self.env[item.modelo].hackGenerarPdfFirmado(int(item.idmodelo), item.fecha_valid, idpersona, estado, None)
        
            file_name = "{0}-{1}.pdf".format(item.modelo, item.idmodelo)
            attach_id = self.env['ir.attachment'].create({
                        'name'  :  file_name,
                        'datas' :  result['result'],
                        'datas_fname' : file_name,
                        'res_model'   : "leulit_signaturedoc",
                        'res_id' : item.id,
                        'type'  :  'binary',
                        'public' : True
                    })
            datosdb = {
                'attachment_id' : attach_id,
                'hashcode': result['hashcode']
            }
            item.write(int(iddocumento), datosdb)
        return True
    
    def export_file( self, cr, uid, ids, context ):
        for item in self.read(cr, uid, ids, ['attachment_id','datas_fname','datas','id']):
            return {
                'type' : 'ir.actions.act_url',
                'url': '/web/signaturedoc/download_document?model=ir.attachment&field=datas&id={0}&filename={1}'.format(item['attachment_id'][0], item['datas_fname']),
                'target': 'self',
            } 


    name = fields.Char('Descripcion', size=500, help="Descripción documento")
    attachment_id = fields.Many2one('ir.attachment','Documento')
    name_attach = fields.Char(related='attachment_id.name')
    datas_fname = fields.Char(string='File Name',size=256, readonly="1")
    datas = fields.Binary(related='attachment_id.datas', string='File Content', readonly=1)
    firma = fields.Binary(string='Firma')
    esignature = fields.Char(string='Firma electrónica')
    hashcode = fields.Char(string='Hash code')
    modelo = fields.Char(string='Entidad')
    referencia = fields.Char(string='Referencia')
    idmodelo = fields.Integer(string='Identificador Entidad')
    firmado_por = fields.Many2one('res.partner', 'Firmado por', ondelete='restrict', readonly=True)
    fecha_create = fields.Datetime(string='Fecha creación')
    fecha_valid = fields.Datetime(string='Fecha validación')
    estado = fields.Char(string='Estado')
    estado_modelo = fields.Char(string='Estado modelo')
    otp_qrcode = fields.Binary(string="QR")
    otp = fields.Char('Código')
    notp = fields.Char('Código')
    qrtext = fields.Char('Cadena QR')
    firmado = fields.Boolean('Firmado')


    