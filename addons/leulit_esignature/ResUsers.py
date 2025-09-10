# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64
import pyotp
import pyqrcode
import io

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _name = "res.users"
    _inherit = "res.users"

    def _otp_secret(self):
        return pyotp.random_base32()

    def _qr_create(self,uri):
        buffer = io.BytesIO()
        qr = pyqrcode.create(uri)
        qr.png(buffer,scale=3)    
        return buffer.getvalue().encode('base64')

    def getOtpObj(self):
        self.get_otp_secret()
        totp = pyotp.TOTP(self.otp_secret, interval=60)
        return totp

    def get_otp(self):        
        totp = self.getOtpObj()
        totp.period = 20
        return totp.now()

    def get_otp_secret(self):
        if not self.otp_secret:
            otp_secret = self._otp_secret()
            self.otp_secret = otp_secret

    def hashEncodeWithSecret(self, tira):
        import hashlib
        #h = hashlib.new(user['otp_secret'])
        h = hashlib.md5()
        h.update(tira.encode('utf-8'))
        return h.hexdigest()


    def check_otp(self, otp_code):
        result = False
        totp = self.getOtpObj()
        result = totp.verify(otp_code)
        return result


    def _otp_qrcode(self):
        for item in self:
            a = ""
            self.otp_qrcode = None

    def _otp_qrandroid(self):
        for item in self:
            a = ""
            '''
            res[item['id']] = self._qr_create(item['otp_urlandroid'])
            '''
            self.otp_qrandroid = None

    def _otp_qrios(self):
        for item in self:
            a = ""
            '''
            res[item['id']] = self._qr_create(item['otp_urlios'])
            '''
            self._otp_qrios = None

    def _otp_uri(self):
        for item in self:
            a=""
            self.otp_uri = ""
            '''
            if item.otp_type == 'time':
                otp = pyotp.TOTP(item['otp_secret'], interval=60)
                otp.period = item['otp_period']
                #~ provisioning_uri = otp.provisioning_uri(self.login,issuer_name=self.company_id.name)
                provisioning_uri = otp.provisioning_uri(item['login'])
            else:
                otp = pyotp.HOTP(item['otp_secret'])
                otp.digits = item['otp_digits']
                provisioning_uri = otp.provisioning_uri(item['login'],item['otp_counter'])

            if item['company_id']:
                res[item['id']] = provisioning_uri + '&issuer=%s' % item['company_id'][1]
            else:
                res[item['id']] = provisioning_uri + '&issuer='
            base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='',context=context,)
            res[item['id']] = "{0}&baseurl={1}".format(res[item['id']], base_url)
            '''

    
    @api.model
    def create(self, vals):
        vals['otp_secret'] = self._otp_secret()
        return super(ResUsers, self).create(vals)

    def registerdevice(self, cr, uid, datos, context=None):
        itemid = self.search(cr, uid, [('id','=',uid)])
        if itemid:
            if isinstance(itemid,list):
                itemid = itemid[0]
            self.write(cr, uid, itemid, {'otp_deviceinfo' : datos['digest']})
            return True
        return False
        
    '''
    def validatedevice(self, cr, uid, datos, context=None):
        result = False
        if 'digest' in datos:
            if datos['digest']:
                if datos['digest'] != '':
                    itemid = self.search(cr, uid, [('otp_deviceinfo','=',datos['digest'])])
                    result = len(itemid) > 0
        return {
            'valid': result
        }


    def removedevice(self, cr, uid, datos, context=None):
        _logger.error("datos = %r",datos)
        itemid = self.search(cr, uid, [('otp_secret','=',datos['secret'])])
        _logger.error("itemid = %r",itemid)
        self.write(cr, uid, itemid, {'otp_deviceinfo' : ""})
        return True
    '''
    def initOTP(self):
        # for iditem in ids:
        #     self.write(cr, uid, iditem, {'otp_secret': self._otp_secret(cr, uid),'otp_deviceinfo':''})
        # return True

        raise UserError('Funcionalidad no migrada boton')

    
    def sendInstallMail(self):
        # template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'leulit_esignature', 'leulit_202009162105_mail')[1]
        # item = self.read(cr,uid, ids, ['id','otp_qrcode','email'], context)
        # if isinstance(item, list):
        #     item = item[0]
        # try:
        #     context.update({'mail_to': item['email']})
        #     context.update({'subject': "Instalación aplicación móvil Helipistas S.L."})

        #     email_template_obj = self.pool.get('email.template')

        #     values = email_template_obj.generate_email(cr, uid, template_id, item['id'], context=context)
        #     mail_mail = self.pool.get('mail.mail')
        #     msg_id = mail_mail.create(cr, uid, values, context=context)
        #     mail = mail_mail.browse(cr, uid, msg_id, context=context)
        #     mail_mail.send(cr, uid, [msg_id], context=context)
        #     #self.pool.get('email.template').send_mail(cr, uid, template_id, item['id'], True, context=context)
        # except Exception as e:
        #     raise osv.except_osv(_('Error enviado email!'), '{0}'.format(e.message))
        # return True    
        raise UserError('Funcionalidad no migrada boton')

        

    def sendQRToRegisterMobile(self):
        # template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'leulit_esignature', 'leulit_202009131035_mail')[1]
        # item = self.read(cr,uid, ids, ['id','otp_qrcode','email'], context)
        # if isinstance(item, list):
        #     item = item[0]
        # try:
        #     context.update({'mail_to': item['email']})
        #     context.update({'subject': "Registro de dispositivo móvil en el ERP de Helipistas S.L."})

        #     ir_attachment = self.pool.get('ir.attachment')
        #     email_template_obj = self.pool.get('email.template')
        #     values = email_template_obj.generate_email(cr, uid, template_id, item['id'], context=context)
        #     mail_mail = self.pool.get('mail.mail')
        #     msg_id = mail_mail.create(cr, uid, values, context=context)
        #     mail = mail_mail.browse(cr, uid, msg_id, context=context)
        #     attachment_data = {
        #     'name': "CÓDIGO QR",
        #     'datas_fname': "qrcode.png",
        #     'datas': item['otp_qrcode'],
        #     'res_model': 'mail.message',
        #     'res_id': mail.mail_message_id.id,
        #     }
        #     attachment_ids = []
        #     attachment_ids.append(ir_attachment.create(cr, uid, attachment_data, context=context))
        #     if attachment_ids:
        #         values['attachment_ids'] = [(6, 0, attachment_ids)]
        #     mail_mail.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)
        #     mail_mail.send(cr, uid, [msg_id], context=context)
        #     #self.pool.get('email.template').send_mail(cr, uid, template_id, item['id'], True, context=context)
        # except Exception as e:
        #     raise osv.except_osv(_('Error enviado email!'), '{0}'.format(e.message))
        # return True
        raise UserError('Funcionalidad no migrada boton')
        

    otp_key = fields.Char(string='OTP key', size=128, help="This is the OTP secret (private) key")
    otp_show = fields.Boolean(string='Show characters')
    otp_type = fields.Selection([('time',_('Time based')),('count',_('Counter based'))],"Type")
    otp_secret = fields.Char(string="Secret",size=16,help='16 character base32 secret')
    otp_counter = fields.Integer(string="Counter")
    otp_digits = fields.Integer(string="Digits",help="Length of the PIN")
    otp_period = fields.Integer(string="Period",help="Number seconds PIN is active")
    otp_qrcode = fields.Binary(compute=_otp_qrcode, store=False, string="QR",)
    otp_qrios = fields.Binary(compute=_otp_qrios, store=False, string="QR IOs",)
    otp_qrandroid = fields.Binary(compute=_otp_qrandroid, store=False, string="QR Android",)
    otp_urlios = fields.Char(string="Iphone App")
    otp_urlandroid = fields.Char(string="Andoid App")
    otp_uri = fields.Char(compute=_otp_uri, store=False, string="URI",)
    otp_deviceinfo = fields.Char(string="Dispositivo registrado")
    can_sign_anomalia = fields.Boolean(string='Usuario puede firmar anomalías')
    can_sign_crs = fields.Boolean(string='Usuario puede firmar CRS')
    can_sign_formone = fields.Boolean(string='Usuario puede firmar Form One')
    can_sign_boroscopia = fields.Boolean(string='Usuario puede firmar Boroscopias')

    '''
    _defaults       = {
        'otp_counter : 1,
        'otp_digits  : 6,
        'otp_period  : 30,
        'otp_type    : 'time',

        'otp_urlios  : 'https://itunes.apple.com/se/app/freeotp-authenticator/id872559395',
        'otp_urlandroid'            : 'https://play.google.com/store/apps/details?id=org.fedorahosted.freeotp'
    }
    '''


    