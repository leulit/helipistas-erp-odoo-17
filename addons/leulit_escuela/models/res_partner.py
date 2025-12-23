# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"


    # def write(self, vals):
    #     if 'is_alumno' in vals and vals['is_alumno'] == True:
    #         alumno = self.env['leulit.alumno'].search([('partner_id','=',self.id)])
    #         if not alumno:
    #             self.env['leulit.alumno'].create({'partner_id':self.id})
    #     if 'is_profesor' in vals and vals['is_profesor'] == True:
    #         alumno = self.env['leulit.profesor'].search([('partner_id','=',self.id)])
    #         if not alumno:
    #             self.env['leulit.profesor'].create({'partner_id':self.id})
    #     return super(res_partner, self).write(vals)


    # @api.model
    # def create(self, vals):
    #     if 'is_alumno' in vals and vals['is_alumno'] == True:
    #         self.env['leulit.alumno'].create({'partner_id':self.id})
    #     if 'is_profesor' in vals and vals['is_profesor'] == True:
    #         self.env['leulit.profesor'].create({'partner_id':self.id})
    #     return super(res_partner, self).create(vals)

    @api.model
    def getProfesor(self):   
        self.ensure_one()             
        for item in self.env['leulit.profesor'].search([('partner_id','=',self.id)]):
            return item.id
        return None


    @api.model
    def getAlumno(self):
        self.ensure_one()
        for item in self.env['leulit.alumno'].search([('partner_id','=',self.id)]):
            return item.id
        return None
        
        
    is_profesor = fields.Boolean(string='Profesor')
    is_alumno = fields.Boolean(string='Alumno')
