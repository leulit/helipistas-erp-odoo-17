# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_revision_mel(models.Model):
    _name           = "leulit.revision_mel"
    _description    = "leulit_revision_mel"
    _order          = "fecha desc"
    

    def _get_tipos(self):
        return utilitylib.leulit_get_tipos_helicopteros() 
    
    
    name = fields.Char('Revisión', size=255,required=True)
    fecha = fields.Date('Fecha',required=True)
    tipo_helicoptero = fields.Selection(_get_tipos,'Tipo')
    