# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_performance(models.Model):
    _name = "leulit.performance"
    _description = "Performance"

    @api.model
    def create(self, vals):
        if 'vuelo' in vals:
            if vals['vuelo']:
                sql = "select id, vuelo from leulit_performance where vuelo = {0} ".format(vals['vuelo'])
                row = self._cr.execute(sql)
                if row:
                    self.write([row['id']], vals)
                    return row['id']
        return super(leulit_performance, self).create(vals)

    def onchange_IGE(self,vuelo_id,binary_performance):
        vuelo_id.write({'canvas_performance_ige': binary_performance})
        self.write({'IGE':binary_performance})
        return True

    def onchange_OGE(self,vuelo_id,binary_performance):
        vuelo_id.write({'canvas_performance_OGE': binary_performance})
        self.write({'OGE':binary_performance})
        return True

    
    peso = fields.Float('Peso')
    temperatura = fields.Float('Temperatura')
    vuelo = fields.Many2one('leulit.vuelo','Vuelo')
    guardar = fields.Boolean('Guardar')
    pulsar_calcular = fields.Boolean('Pulsar Calcular')
    ige = fields.Binary('IGE', attachment=False)
    oge = fields.Binary('OGE', attachment=False)

    def save_performance(self):
        context = self.env.context
        self.write({'temperatura':context['temperatura'],'guardar':True})
        return True
