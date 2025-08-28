# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class leulit_checklist_template_item(models.Model):
    _name           = "leulit.checklist_template_item"
    _description    = "leulit_checklist_template_item"
    _rec_name       = "descriptor"
    _order          = "orden"
    

    descriptor = fields.Char("Descriptor", required=True)
    checklist_template_id = fields.Many2one('leulit.checklist_template', 'Checklist')
    orden = fields.Integer("Orden")


    '''
    def init(self, cr):
        sql ="""
            SELECT * FROM leulit_checklist_template_item_rel
        """
        rows = utilitylib.runQuery(cr, sql)
        _logger.error("--->rows_template")
        for row in rows:
            sql ="""
                SELECT * FROM leulit_checklist_item WHERE id = {0}
            """.format(row['checklist_item_id'])
            item = utilitylib.runQueryReturnOne(cr, sql)        
            if item:
                self.create(cr, SUPERUSER_ID, {
                    'checklist_template_id'         : row['checklist_template_id'],
                    'descriptor'                    : item['descriptor'],
                    'comentarios'                   : item['comentarios'],
                })
    '''
