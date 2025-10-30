# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_lines_mel(models.Model):
    _name           = "leulit.lines_mel"
    _description    = "leulit_lines_mel"
    _rec_name       = "referencia"
    

    def _get_categorias(self):
        return (
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D')
        )
    
    
    referencia = fields.Char('Referencia', )
    tenerencuenta = fields.Text('Puntos de interés / Excepciones')
    categoria = fields.Selection(_get_categorias,'Categoría')
    numinstalado = fields.Integer('Nº instalados')
    numexp = fields.Char('Nº expedición', )
    tipo = fields.Many2one('leulit.mel_tipo_operacion', 'Tipo')
    mel_id = fields.Many2one('leulit.mel', 'MEL')
    