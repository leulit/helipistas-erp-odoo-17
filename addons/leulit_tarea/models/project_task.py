# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, api, models
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = ["project.task"]


    @api.onchange('stage_id')
    def onchange_stage_id(self):
        if self.stage_id:
            if self.stage_id.name in ['Hecho','Realizada','Finalizado']:
                self.date_finish = datetime.now()


    def _get_default_project(self):
        return self.env['project.project'].search([('name','=','Internal'),('company_id','=',self.env.company.id)])
    
    @api.depends('project_id')
    def _get_project_is_borrador(self):
        estado_borrador = self.env['project.status'].search([('name', '=', 'En borrador')])
        for item in self:
            if item.project_id:
                if item.project_id.project_status.id == estado_borrador.id:
                    item.project_borrador = True
                else:
                    item.project_borrador = False
            else:
                item.project_borrador = False

    def _search_project_is_borrador(self, operator, value):
        estado_borrador = self.env['project.status'].search([('name', '=', 'En borrador')])
        if operator == '=':
            operator = '!='
        elif operator == '!=':
            operator = '='
        else:
            raise ValueError("Invalid operator for search_project_is_borrador")
        return [('project_id.project_status', operator, estado_borrador.id)]

    project_id = fields.Many2one('project.project', string='Project',
        compute='_compute_project_id', store=True, readonly=False,
        index=True, tracking=True, check_company=True, change_default=True, default=_get_default_project)
    new_priority = fields.Selection([
        ('0', 'Sin prioridad'),
        ('1', 'Se puede trabajar, Persona'),
        ('2', 'Se puede trabajar, Grupo'),
        ('3', 'Se puede trabajar, Todos'),
        ('4', 'Se puede trabajar con problemas, Persona'),
        ('5', 'Se puede trabajar con problemas, Grupo'),
        ('6', 'Se puede trabajar con problemas, Todos'),
        ('7', 'No se puede trabajar, Persona'),
        ('8', 'No se puede trabajar, Grupo'),
        ('9', 'No se puede trabajar, Todos'),
    ], index=True, string="Prioridad")
    project_borrador = fields.Boolean(compute=_get_project_is_borrador, string="Borrador", search=_search_project_is_borrador)

    
