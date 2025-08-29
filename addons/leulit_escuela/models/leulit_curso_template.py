# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class leulit_curso_template(models.Model):
    _name           = "leulit.curso_template"
    _description    = "leulit_curso_template"
    _rec_name       = "name"

    def action_create_revision(self):
        return {
            'name': _('Crear Edición/Revision'),
            'type': 'ir.actions.act_window',
            'res_model': 'leulit.curso',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_template_id': self.id,
                'default_ato_mo': self.ato_mo,
                'default_ato_mi': self.ato_mi,
                'default_aoc': self.aoc,
                'default_ttaa': self.ttaa,
                'default_nco': self.nco,
                'default_lci': self.lci,
                'default_camo': self.camo,
                'default_p_145': self.p_145,
            }
        }

    name = fields.Char(string='Descripción', required=True)
    ato_mo = fields.Boolean('ATO MI')
    ato_mi = fields.Boolean('ATO MO')
    nco = fields.Boolean('NCO')
    aoc = fields.Boolean('AOC')
    ttaa = fields.Boolean('TTAA')
    lci = fields.Boolean('LCI')
    camo = fields.Boolean('CAMO')
    p_145 = fields.Boolean('Parte 145')
    revisiones = fields.One2many(comodel_name='leulit.curso', inverse_name='template_id', string='Revisiones')

    @api.constrains('ato_mi', 'ato_mo', 'aoc', 'ttaa', 'lci', 'camo', 'p_145', 'nco')
    def _check_at_least_one_boolean(self):
        for record in self:
            if not (record.ato_mo or record.ato_mi or record.aoc or record.ttaa or record.lci or record.camo or record.p_145):
                raise ValidationError(_("Debe marcar al menos uno de los siguientes campos: AOC, LCI, ATO MO, ATO MI, TTAA, NCO, CAMO o Parte 145."))