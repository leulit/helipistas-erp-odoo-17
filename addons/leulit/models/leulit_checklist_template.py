# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class leulit_checklist_template(models.Model):
    _name = "leulit.checklist_template"
    _description = "leulit_checklist_template"
    _rec_name = "descriptor"
    _inherit = ['mail.thread']


    def checklist_print_report(self):
        for rec in self:
            items_checklist = []
            for item in rec.items:
                items_checklist.append({
                    'descriptor' : item.descriptor,
                    'orden' : item.orden,
                })
            data = {
                'items' : items_checklist,
                'descriptor':  'Plantilla: {0}'.format(rec.descriptor),
            }
            return self.env.ref('leulit.report_leulit_checklist_template').report_action([],data=data)


    tags = fields.Many2many('leulit.checklist_tag', 'leulit_checklist_template_tag_rel', 'checklist_template_id','checklist_tag_id', 'Clasificación')
    descriptor = fields.Char("Descriptor", size=500, required=True)
    comentarios = fields.Text("Comentarios")
    usuarios = fields.Many2many('res.users','leulit_checklist_template_user_rel','checklist_template_id','user_id','Destinatarios')
    items = fields.One2many('leulit.checklist_template_item','checklist_template_id','Items')
    state = fields.Selection([('2','Borrador'),('1','Activo'),('0','Inactivo')], 'Estado')
    tiempo_previsto = fields.Float(string="Tiempo previsto")
    active = fields.Boolean(string='Activo',default=True)
    project_id = fields.Many2one('project.project', 'Proyecto', default=1)
    # steps = fields.One2many('leulit_cti', 'checklist_template_id', 'Steps')
