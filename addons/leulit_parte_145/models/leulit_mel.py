# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_mel(models.Model):
    _name           = "leulit.mel"
    _description    = "leulit_mel"
    _rec_name       = "name"
    

    def _get_tipos(self):
        return utilitylib.leulit_get_tipos_helicopteros()
    

    @api.depends('helicoptero_ids')
    def _get_helicopteros_mel(self):
        for item in self:
            texto=''
            for heli in item.helicoptero_ids:
                texto = texto + heli.name + "\n"
            item.matriculas_heli = texto


    referencia = fields.Char('Referencia', size=20)
    name = fields.Char('Descripción', size=255)
    helicoptero_ids = fields.Many2many('leulit.helicoptero', 'leulit_helicoptero_mel_rel','mel_id' ,'helicoptero_id','Helicópteros',domain="[('baja','=',False)]")
    linemel_ids = fields.One2many('leulit.lines_mel', 'mel_id', 'Diferidos')
    ata = fields.Many2one('leulit.mel_ata', 'ATA')
    tipo_helicoptero = fields.Selection(_get_tipos,'Tipo')
    matriculas_heli = fields.Text(compute='_get_helicopteros_mel',string='Helicópteros')
    revision_id = fields.Many2one('leulit.revision_mel', 'Revisión')
    fecha_revision = fields.Date(related='revision_id.fecha',string='Fecha Revisión',readonly=True)
