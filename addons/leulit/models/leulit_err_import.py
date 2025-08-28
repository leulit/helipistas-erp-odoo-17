# -*- encoding: utf-8 -*-
from odoo.addons.leulit import utilitylib
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
import base64
import time
from datetime import timedelta
from re import search
import xmlrpc.client
import threading
_logger = logging.getLogger(__name__)

from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)

from datetime import datetime, date, timedelta


class leulit_error_import(models.Model):
    _name = "leulit.error_import"
    _description = "Datos importación"


    tabla = fields.Char(string='Tabla',)
    campos = fields.Text(string='Campos',)
    datos = fields.Text(String='Datos',)
    comments = fields.Text(String='Comentarios',)
    fecha = fields.Datetime(String='Fecha',)