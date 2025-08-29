# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class leulit_actividad_base_year(models.Model):
    _name = "leulit.actividad_base_year"
    _description = "leulit_actividad_base_year"
    _auto = False
    _order = "year desc, partner"

    
    '''
    def init(self):
        tools.drop_view_if_exists(self._cr, 'actividad_base_year')
        self._cr.execute(""" CREATE OR REPLACE VIEW actividad_base_year AS 
            (
                 SELECT leulit_actividad_base_year.partner,
                    leulit_actividad_base_year.year,
                    sum(leulit_actividad_base_year.tiempo) AS tiempo,
                    row_number() OVER () AS id
                FROM ( SELECT leulit_actividad_base_dia.partner,
                            date_part('year'::text, leulit_actividad_base_dia.fecha) AS year,
                            leulit_actividad_base_dia.tiempo
                        FROM leulit_actividad_base_dia
                        WHERE leulit_actividad_base_dia.prevista = 'f'
                    ) leulit_actividad_base_year
                GROUP BY leulit_actividad_base_year.partner, leulit_actividad_base_year.year
                ORDER BY leulit_actividad_base_year.partner, leulit_actividad_base_year.year DESC
            )
        """)
    '''

    # def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
    #     res = super(leulit_actividad_base_year, self).read_group(cr, uid, domain, fields, groupby, offset, limit=limit, context=context, orderby=orderby)
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
        res = {}
        for item in self:     
            item.tiempo_facturable = self.env['leulit.actividad_base_dia'].getTiempoFacturableYear(item.partner.id, item.year)            


    def detalle(self):
        return True
    #     view_ref = self.pool.get('ir.model.data')._xmlid_to_res_model_res_id(cr. uid, 'leulit_actividad', 'leulit_202012111314_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     item = self.browse(cr, uid, ids)[0]
    #     sql = '''
    #         SELECT id FROM actividad_base_mes WHERE year = {0} AND user_id = {1}
    #     '''.format( int(item.year), item.user_id.id)        
    #     rows = self.runQuery(cr, sql)
    #     itemsIds = [ x['id'] for x in rows ]        
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Detalle actividad año {0}'.format(item.year),
    #         'res_model': 'actividad_base_mes',
    #         'view_type': 'form',
    #         'view_mode': 'tree',
    #         'view_id': view_id,
    #         'res_id': itemsIds,
    #         'context': context,
    #         'initial_mode': 'view',
    #         'target': 'self',
    #         'multi': "True",
    #         'domain': [('id','in',itemsIds)],
    #         'flags' : {'form': {'action_buttons': False}}
    #     }    


    partner = fields.Many2one(comodel_name='res.partner', string='Usuario')
    year = fields.Integer('Año')
    tiempo = fields.Float('Tiempo', digits=(16, 2))
    tiempo_facturable = fields.Float(compute='_tiempo_facturable',string='tiempo facturable',store=False, digits=(16, 2))
    # uid_ok = fields.Boolean(compute='_uid_ok',string='',store=False,search=_search_uid_ok)


    