# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class leulit_checklist_item(models.Model):
    _name           = "leulit.checklist_item"
    _description    = "leulit_checklist_item"
    _rec_name       = "descriptor"
    _order          = "doit, orden"
    

    def checklist_item_doit(self):
        hoy = datetime.now()
        self.write({'doit': True,'fecha_doit': hoy})
        for item in self:
            item.checklist_id.updFinalizado()
        return True


    descriptor = fields.Char("Descriptor", required=True)
    checklist_id = fields.Many2one('leulit.checklist', 'Checklist')
    orden = fields.Integer("Orden")
    doit = fields.Boolean('Hecho')
    fecha_doit = fields.Datetime("Fecha realización")



    '''
    def init(self, cr):
        sql ="""
            SELECT * FROM leulit_checklist_checklist_item_rel
        """
        rows = utilitylib.runQuery(cr, sql)
        for row in rows:
            self.write(cr, SUPERUSER_ID, row['checklist_item_id'], {
                'checklist_id' : row['checklist_id']
            })
    '''