from odoo import api, models, fields
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class LeulitModificationsAndRepairs(models.Model):
    _name = "leulit.modifications_and_repairs"
    _description = "Modifications and Repairs"
    _rec_name = "modification_doc"

    modification_doc = fields.Char(string="Modification Document", required=True)
    rev = fields.Char(string="Revision")
    approval_date = fields.Date(string="Approval Date")
    description = fields.Text(string="Description", required=True)
    application_date = fields.Date(string="Application Date")
    work_order = fields.Char(string="Work Order")
    preflight_inspection_affectation = fields.Boolean(string="Preflight Inspection Affectation")
    ica_associated = fields.Boolean(string="ICA Associated")
    impact_on_weight_and_balance = fields.Boolean(string="Impact on w&b")
    last_weight_and_balance_with_modification = fields.Char(string="Last Weight and Balance with Modification")
    date_unmodified = fields.Date(string="Date Unmodified")
    notes = fields.Text(string="Notes")