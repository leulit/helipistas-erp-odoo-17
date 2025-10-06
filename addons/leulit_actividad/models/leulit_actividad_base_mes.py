# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class leulit_actividad_base_mes(models.Model):
    _name = "leulit.actividad_base_mes"
    _description = "leulit_actividad_base_mes"
    _auto = False
    _order = "year desc, month desc, partner"

    
    '''
    def init(self):
        tools.drop_view_if_exists(self._cr, 'actividad_base_mes')
        self._cr.execute(""" CREATE OR REPLACE VIEW actividad_base_mes AS 
            (
                 SELECT leulit_actividad_base_mes.partner,
                    leulit_actividad_base_mes.year,
                    leulit_actividad_base_mes.month,
                    sum(leulit_actividad_base_mes.tiempo) AS tiempo,
                    row_number() OVER () AS id
                FROM ( SELECT leulit_actividad_base_dia.partner,
                            date_part('month'::text, leulit_actividad_base_dia.fecha) AS month,
                            date_part('year'::text, leulit_actividad_base_dia.fecha) AS year,
                            leulit_actividad_base_dia.tiempo
                        FROM leulit_actividad_base_dia
                        WHERE leulit_actividad_base_dia.prevista = 'f') leulit_actividad_base_mes
                GROUP BY leulit_actividad_base_mes.partner, leulit_actividad_base_mes.year, leulit_actividad_base_mes.month
                ORDER BY leulit_actividad_base_mes.partner, leulit_actividad_base_mes.year DESC, leulit_actividad_base_mes.month DESC 
            )
        """)
    '''

    # def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
    #     res = super(actividad_base_mes, self).read_group(cr, uid, domain, fields, groupby, offset, limit=limit, context=context, orderby=orderby)
    #     return res

    # def _uid_ok(self, cr, uid, ids, field_name, field_args,  context=None):       
    #     res = {}
    #     for item in self.read(cr, uid, ids, ['user_id', 'id'], context=context):            
    #         res[item['id']] = uid == item['user_id'][0]
    #     return res


    # def _search_uid_ok(self, cr, uid, obj, name, args, context=None):
    #     context = context or {}
    #     ids = self.search(cr, uid, [], context=context)
    #     items = self.read(cr, uid, ids, ['uid_ok'], context=context)
    #     res = []
    #     for item in items:
    #         if condition(args[0][1], item['uid_ok'], args[0][2]):
    #             res.append(item['id'])
    #     return [('id', 'in', res)]          

    def _tiempo_facturable(self):
        for item in self:     
            item.tiempo_facturable = self.env['leulit.actividad_base_dia'].getTiempoFacturableMesYear(item.partner.id, item.month, item.year)


    def detalle(self):
        return True
    # def detalle(self, cr, uid, ids, context=None):
    #     view_ref = self.pool.get('ir.model.data')._xmlid_to_res_model_res_id(cr. uid, 'leulit_actividad', 'leulit_20201211_1750_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     item = self.browse(cr, uid, ids)[0]
    #     sql = '''
    #         SELECT id FROM actividad_base WHERE EXTRACT(MONTH from fecha) = {0} AND EXTRACT(YEAR from fecha) = {1} AND partner = {2}
    #     '''.format( int(item.month), int(item.year), item.partner.id)        
    #     rows = utilitylib.runQuery(cr, sql)
    #     itemsIds = [ x['id'] for x in rows ]        
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Detalle actividad mes',
    #         'res_model': 'actividad_base',
    #         'view_type': 'form',
    #         'view_mode': 'tree',
    #         'view_id': view_id,
    #         'res_id': rows,
    #         'res_id': itemsIds,
    #         'context': context,
    #         'initial_mode': 'view',
    #         'target': 'new',
    #         'domain': [('id','in',itemsIds)],
    #         'flags' : {'form': {'action_buttons': False}}
    #     }    


    partner = fields.Many2one('res.partner', 'Usuario', ondelete='restrict', index=True)
    month = fields.Integer('Mes')
    year = fields.Integer('Año')
    tiempo = fields.Float('Tiempo', digits=(16, 2))
    tiempo_facturable = fields.Float( compute=_tiempo_facturable,store=False, digits=(16, 2))
    # uid_ok = fields.Boolean( compute=_uid_ok, store=False, fnct_search=_search_uid_ok)
     

    