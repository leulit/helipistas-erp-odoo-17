# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_mel_ata(models.Model):
    _name           = "leulit.mel_ata"
    _description    = "leulit_mel_ata"
    _rec_name       = "ata_name"
    
    
    def _get_name(self):
        for item in self:
            if item.num and item.name:
                item.ata_name = 'ATA '+str(item.num)+" "+item.name
            else:
                item.ata_name = ""
        

    name = fields.Char('Descripción', required=True)
    num = fields.Integer('Nº',required=True)
    ata_name = fields.Char(compute=_get_name,string='ATA')
    