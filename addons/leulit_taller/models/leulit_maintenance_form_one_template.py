# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
from odoo import fields, models, api
from datetime import datetime, date, timedelta, time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class LeulitMaintenanceFormOneTemplate(models.Model):
    _name = "leulit.maintenance_form_one_template"


    @api.constrains('remarks')
    def _check_remarks_lines(self):
        MAX_LINES = 7
        for record in self:
            _logger.error('REMARKS: %s', record.remarks)
            if record.remarks:
                # Contar etiquetas <p>
                num_lines = len(re.findall(r'<p[^>]*>', record.remarks))
                # Si no hay etiquetas <p>, contar <br> + 1
                if num_lines == 0:
                    num_lines = record.remarks.count('<br') + 1
                
                if num_lines > MAX_LINES:
                    raise ValidationError(f'El campo Remarks no puede tener más de {MAX_LINES} líneas.')

    name = fields.Char(string="Nombre Plantilla")
    remarks = fields.Text(string="Remarks", default="")