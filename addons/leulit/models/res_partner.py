# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
import threading
import warnings

_logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    def create_user_by_partner(self):
        try:
            self.env['res.users'].create({
                'login' : self.email,
                'name' : self.name,
                'partner_id' : self.id,
                'lang': 'es_ES',
                'company_id': 1,
                'sel_groups_1_9_10': 10,
                'property_stock_customer' : None,
                'property_stock_supplier' : None,
            })
        except:
            raise UserError("No se ha podido crear el usuario, revisa que el contacto tenga Email.")

    def get_next_accounts(self):
        cuentas = self.env['account.account'].search([])
        codigo_max_cobrar = 0
        codigo_max_pagar = 0
        for cuenta in cuentas:
            if cuenta.code and cuenta.code != '\xa0':
                codigo = int(cuenta.code)
                if codigo > 43000000 and codigo < 43005000:
                    if codigo > codigo_max_cobrar:
                        codigo_max_cobrar = codigo
                if codigo > 41000000 and codigo < 41040000:
                    if codigo > codigo_max_pagar:
                        codigo_max_pagar = codigo
        for item in self:
            try:
                account_cobrar = self.env['account.account'].create({'code':str(codigo_max_cobrar+1),'name':item.name,'user_type_id':1,'reconcile':True,'company_id':1})
                account_pagar = self.env['account.account'].create({'code':str(codigo_max_pagar+1),'name':item.name,'user_type_id':2,'reconcile':True,'company_id':1})
                item.property_account_receivable_id = account_cobrar.id
                item.property_account_payable_id = account_pagar.id
                item.bool_cuentas_custom = True
                codigo_max_pagar = codigo_max_pagar+1
                codigo_max_cobrar = codigo_max_cobrar+1
            except Exception as e:
                raise UserError ('No se ha podido asignar las cuentas, comunicalo a IT (code intentado: %s / %s).' % (str(codigo_max_cobrar+1),str(codigo_max_pagar+1)))

    def _recalcular_complete_name_thread(self, dbname, uid):
        """Función interna que se ejecuta en el thread"""
        with api.Environment.manage():
            new_cr = registry(dbname).cursor()
            try:
                env = api.Environment(new_cr, uid, {})
                warnings.filterwarnings('ignore')
                
                partners = env['res.partner'].search([])
                total = len(partners)
                _logger.info('Iniciando recálculo de complete_name para %s partners', total)
                
                for idx, partner in enumerate(partners, 1):
                    try:
                        partner._compute_complete_name()
                        if idx % 100 == 0:
                            _logger.info('Procesados %s/%s partners', idx, total)
                            new_cr.commit()
                    except Exception as e:
                        _logger.error('Error al calcular complete_name para partner %s: %s', partner.id, str(e))
                
                new_cr.commit()
                _logger.info('Recálculo de complete_name completado para %s partners', total)
            except Exception as e:
                _logger.error('Error en thread de recálculo: %s', str(e))
                new_cr.rollback()
            finally:
                new_cr.close()

    def recalcular_complete_name_async(self):
        """Método público para lanzar el recálculo en un thread"""
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Solo los administradores pueden ejecutar esta acción.')
        
        dbname = self.env.cr.dbname
        uid = self.env.uid
        
        thread = threading.Thread(
            target=self._recalcular_complete_name_thread,
            args=(dbname, uid)
        )
        thread.daemon = True
        thread.start()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recálculo iniciado',
                'message': 'El recálculo de complete_name se está ejecutando en segundo plano. Revisa los logs para ver el progreso.',
                'type': 'success',
                'sticky': False,
            }
        }
                


    bool_cuentas_custom = fields.Boolean(string="",default=False)
    firma = fields.Binary('Firma')
    sello = fields.Binary('Sello')
    peso_piloto = fields.Float('Peso Piloto')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',default=68)
    lang = fields.Selection(_lang_get, string='Language',help="All the emails and documents sent to this contact will be translated in this language.", default="es_ES")
    alumno_erp = fields.Integer(string='alumno_erp')
    piloto_erp = fields.Integer(string='piloto_erp')
    profesor_erp = fields.Integer(string='profesor_erp')
    empleado_erp = fields.Integer(string='empleado_erp')
    partner_erp = fields.Integer(string='partner_erp')
    user_id_erp = fields.Integer(string='user_erp')