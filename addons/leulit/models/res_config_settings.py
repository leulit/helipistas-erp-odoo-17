# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)



class ResConfigSettings(models.TransientModel):
   
    _inherit = 'res.config.settings'

    flight_hours_project = fields.Many2one(
        comodel_name='project.project', 
        string='Proyecto horas de vuelo',
        config_parameter='leulit.flight_hours_project',
    )
    school_hours_project = fields.Many2one(
        comodel_name='project.project', 
        string='Proyecto horas de escuela',
        config_parameter='leulit.school_hours_project',
    )
    meeting_hours_project = fields.Many2one(
        comodel_name='project.project', 
        string='Proyecto horas de reuniones',
        config_parameter='leulit.meeting_hours_project',
    )
    maintenance_hours_project = fields.Many2one(
        comodel_name='project.project', 
        string='Proyecto horas de mantenimiento',
        config_parameter='leulit.maintenance_hours_project',
    )



    '''
    def set_values(self):
       res = super(ResConfigSettings, self).set_values()  
       self.env['ir.config_parameter'].set_param('leulit_modules.flight_hours_project', self.flight_hours_project.id)
       self.env['ir.config_parameter'].set_param('leulit_modules.school_hours_project', self.school_hours_project.id)
       return res


    def get_values(self):
       res = super(ResConfigSettings, self).get_values()
       value1 = self.env['ir.config_parameter'].sudo().get_param('leulit_modules.flight_hours_project')
       value2 = self.env['ir.config_parameter'].sudo().get_param('leulit_modules.school_hours_project')
       res.update(
           flight_hours_project = value1,
           school_hours_project = value2
       )
       return res
    '''