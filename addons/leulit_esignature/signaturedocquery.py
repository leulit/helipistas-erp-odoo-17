# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64

_logger = logging.getLogger(__name__)


class SignatureDocQuery(models.Model):
    _name = "leulit_signaturedocquery"
    _description = "leulit_signaturedocquery"
   
    def doquery(self, cr, uid, ids, csvcode, context=None):
        atributos_search = [('hashcode', '=', csvcode)]

        leulit_signaturedoc = self.pool['leulit_signaturedoc']
        itemsId = leulit_signaturedoc.search(cr, uid, atributos_search, order="fecha_create desc")
        items = []
        if itemsId:
            if not isinstance(itemsId, list):
                itemsId = [itemsId]
            items = leulit_signaturedoc.read(cr, uid, itemsId, [])
            '''
            if items and len(items) > 0:
                item = items[0]
                itemsId = leulit_signaturedoc.search(cr, uid, [('modelo','=',item['modelo']),('idmodelo','=',item['idmodelo']),('fecha_create','>=',item['fecha_create'])], order="fecha_create desc")
                items = leulit_signaturedoc.read(cr,uid,itemsId,[])
            '''
        return {
            'items'     : items,
            'nitems'    : len(items)
        }


    
    csvcode = fields.Char('CSV Code',  help="Código CSV")


    