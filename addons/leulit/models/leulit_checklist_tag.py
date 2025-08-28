# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class leulit_checklist_tag(models.Model):
    _name = "leulit.checklist_tag"
    _description = "leulit_checklist_tag"
    _rec_name = "descriptor"


    descriptor = fields.Char("Descriptor", size=100, required=True)
    res_model = fields.Char('Resource Model',size=64, readonly=True, help="The database object this attachment will be attached to")
    res_id = fields.Integer('Resource ID', readonly=True, help="The record id this is attached to")
