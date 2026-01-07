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
        # Buscar incluyendo archivados para detectar el problema
        profesor = self.env['leulit.profesor'].with_context(active_test=False).search([('partner_id','=',self.id)], limit=1)
        if profesor:
            if not profesor.active:
                raise UserError(_(
                    "El Profesor está archivado y no puede ser utilizado.\n\n"
                    "Profesor: %s (ID: %s)\n"
                    "Partner: %s (ID: %s)\n\n"
                    "Por favor, reactive el profesor desde su ficha para poder continuar."
                ) % (profesor.name, profesor.id, self.name, self.id))
            return profesor.id
        return None


    @api.model
    def getAlumno(self):
        self.ensure_one()
        # Buscar incluyendo archivados para detectar el problema
        alumno = self.env['leulit.alumno'].with_context(active_test=False).search([('partner_id','=',self.id)], limit=1)
        if alumno:
            if not alumno.active:
                raise UserError(_(
                    "El Alumno está archivado y no puede ser utilizado.\n\n"
                    "Alumno: %s (ID: %s)\n"
                    "Partner: %s (ID: %s)\n\n"
                    "Por favor, reactive el alumno desde su ficha para poder continuar."
                ) % (alumno.name, alumno.id, self.name, self.id))
            return alumno.id
        return None
        
        
    is_profesor = fields.Boolean(string='Profesor')
    is_alumno = fields.Boolean(string='Alumno')
