# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class Product(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    @api.depends('categ_id')
    def _get_is_product_taller(self):
        categoria_parent = self.env['product.category'].search([('name','in',['TALLER','BIDONES-TANQUES COMBUSTIBLE'])])
        categorias = self.env['product.category'].search([('parent_id','=',categoria_parent.id)])
        for item in self:
            item.is_product_taller = False
            if item.categ_id:
                if item.categ_id.id in categorias.ids:
                    item.is_product_taller = True


    def _search_is_product_taller(self, operator, value):
        ids = []
        categoria_parent = self.env['product.category'].search([('name','in',['TALLER','BIDONES-TANQUES COMBUSTIBLE'])])
        categorias = self.env['product.category'].search([('parent_id','in',categoria_parent.ids)])
        for item in self.search([]):
            if operator == '=':
                if item.categ_id.id in categorias.ids:
                    ids.append(item.id)
            else:
                if item.categ_id.id not in categorias.ids:
                    ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]


    @api.onchange('optional_product_ids')
    def onchange_optional_product(self):
        if self._origin.optional_product_ids.ids < self.optional_product_ids.ids:
            for product in self.optional_product_ids:
                ids = []
                for producttmpl in product.optional_product_ids:
                    if producttmpl._origin.id != self._origin.product_tmpl_id.id:
                        ids.append(producttmpl._origin.id)
                ids.append(self._origin.product_tmpl_id.id)
                product._origin.optional_product_ids = [(6,0,ids)]
        else:
            list_products_remove = []
            for product in self._origin.optional_product_ids:
                if product.id not in self.optional_product_ids._origin.ids:
                    list_products_remove.append(product)

            for product in list_products_remove:
                ids = []
                for producttmpl in product.optional_product_ids:
                    if producttmpl.id != self._origin.product_tmpl_id.id:
                        ids.append(producttmpl.id)
                product._origin.optional_product_ids = [(6,0,ids)]

    @api.depends('optional_product_ids')
    def _get_pn_equivalencia(self):
        for item in self:
            pn_equiv = ""
            qty = 0
            for x in item.optional_product_ids:
                if x.default_code:
                    pn_equiv += x.default_code + "; "
                qty += x.qty_available
            item.str_product_opcionales = pn_equiv
            item.qty_opcionales = qty


    id_product_almacen = fields.Integer(string='ID Product Antiguo')
    is_product_taller = fields.Boolean(compute=_get_is_product_taller ,string="¿Es un producto de taller?", store=False, search=_search_is_product_taller)
    str_product_opcionales = fields.Char(compute="_get_pn_equivalencia", string="PN alternativos")
    qty_opcionales = fields.Float(compute="_get_pn_equivalencia", string="Qty total alternativos")


    @api.constrains("default_code")
    def _check_unique_default_code(self):
        for item in self:
            if item.default_code:
                products = self.search([('default_code','=',item.default_code),('id','!=',item.id)])
                if len(products) > 0:
                    raise ValidationError("Ya existe otro producto con esta referencia interna / PN.")