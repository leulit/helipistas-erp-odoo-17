# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_control_th(models.Model):
    _name = "leulit.control_th"
    _description = "leulit_control_th"
    _rec_name = "descripcion"
    _order = "to_date desc"



    descripcion = fields.Char('Descripción', required=True)
    from_date = fields.Date('Fecha inicio')
    to_date = fields.Date('Fecha fin')
    hr_employee = fields.Many2one('hr.employee', 'Empleado', )
    attachment_ids = fields.Many2many('ir.attachment', 'control_th_ir_attachments_rel', 'control_th_id', 'attachment_id','Adjuntos')
    observaciones = fields.Text('Observaciones')