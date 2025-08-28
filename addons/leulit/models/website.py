# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import json
import os
import logging
import pytz
import requests
import werkzeug.urls
import werkzeug.utils
import werkzeug.wrappers

from itertools import islice
from xml.etree import ElementTree as ET
from collections import OrderedDict
from operator import itemgetter
from urllib.parse import urlencode  # ✅ Añadido para construir la query string

import odoo

from odoo import http, models, fields, _
from odoo.http import request
from werkzeug.utils import redirect
from odoo.tools import OrderedSet
from odoo.addons.http_routing.models.ir_http import slug, slugify, _guess_mimetype
from odoo.addons.web.controllers.main import Binary
from odoo.addons.portal.controllers.web import Home
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import OR

# Completely arbitrary limits
MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT = IMAGE_LIMITS = (1024, 768)
LOC_PER_SITEMAP = 45000
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)


# class Home(http.Controller):

#     @http.route('/', type='http', auth="none")
#     def index(self, s_action=None, db=None, **kw):
#         query_string = urlencode(request.params)
#         url = '/web'
#         if query_string:
#             url += '?' + query_string
#         return redirect(url)


# class Website(Home):

#     @http.route('/', type='http', auth="public", website=True, sitemap=True)
#     def index(self, **kw):
#         query_string = urlencode(request.params)
#         url = '/web'
#         if query_string:
#             url += '?' + query_string
#         return redirect(url)

# TODO poner en modulo esignature
# class CustomerPortal(CustomerPortal):

#     @http.route(['/verifycsv'], type='http', auth="public", website=True)
#     def portal_verify_csv(self, page=1, date_begin=None, date_end=None, search=None, search_in='content', **kw):
#         values = self._prepare_portal_layout_values()
#         searchbar_inputs = {
#             'content': {'input': 'content', 'label': _('Buscar <span class="nolabel"> (código CSV / CID)</span>')},
#         }
#         domain = [('esignature', '=', 'aaaaaaaaa')]
#         # search
#         if search and search_in:
#             domain = ['|', ('esignature', '=', search), ('hashcode', '=', search)]
        
#         docs = request.env['leulit_signaturedoc'].search(domain, limit=self._items_per_page)

#         values.update({
#             'date': date_begin,
#             'date_end': date_end,
#             'grouped_docs': docs,
#             'page_name': 'Verificar documentos',
#             'default_url': '/verifycsv',
#             'searchbar_inputs': searchbar_inputs,
#             'search_in': search_in,
#             'search': search,
#         })
#         return request.render("leulit.portal_verifycsv", values)
