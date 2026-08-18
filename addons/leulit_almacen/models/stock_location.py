# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
import pyqrcode

_logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = 'stock.location'

    def _get_qr(self):
        for item in self:
            item.qr = False
            # Formato del QR de estanteria: "EST | id | nombre". El prefijo la distingue del QR
            # de caja ("CAJA | id | nombre") y del de pieza ("id | producto"). La app parte la
            # cadena por "|" y hace trim de cada trozo, asi que los espacios dan igual.
            # Solo tienen QR las estanterias, no cualquier ubicacion: una etiqueta pegada en
            # "ICA/Stock" no significa nada.
            if isinstance(item.id, int) and item.name and item.es_estanteria:
                tiraqr = "EST | %s | %s" % (item.id, item.name)
                qr = pyqrcode.create(tiraqr, mode='binary')
                item.qr = qr.png_as_base64_str(3)


    @api.depends('location_id')
    def _get_es_estanteria(self):
        raices = self.env['stock.quant.package']._raices_estanterias()
        for item in self:
            padre = item.location_id
            while padre and padre not in raices:
                padre = padre.location_id
            item.es_estanteria = bool(padre)


    qr = fields.Binary(compute=_get_qr, store=False, string='QR')
    es_estanteria = fields.Boolean(
        compute=_get_es_estanteria, store=False, string='Es estantería',
        help="Cuelga de una de las dos raíces de estanterías. Sirve para no ofrecer la etiqueta "
             "con QR en ubicaciones que no son estanterías.")


    @api.constrains('location_id', 'company_id')
    def _check_estanteria_company(self):
        """Una estanteria tiene que ser de la misma compania que su raiz. Si no, desaparece para
        los usuarios de la compania de la raiz (la regla multi-compania la oculta) y aparece para
        los de la otra: el resultado es que alguien crea una estanteria y no la vuelve a ver."""
        raices = self.env['stock.quant.package']._raices_estanterias()
        for item in self:
            raiz = item.location_id
            while raiz and raiz not in raices:
                raiz = raiz.location_id
            if raiz and item.company_id != raiz.company_id:
                raise ValidationError(_(
                    'La estantería "%s" es de %s, pero cuelga de "%s", que es de %s. '
                    'Los almacenes de las dos compañías están separados.') % (
                        item.name, item.company_id.name or _('ninguna compañía'),
                        raiz.name, raiz.company_id.name))


    def unlink(self):
        """Protege las dos raíces de estanterías. stock.location.location_id es ondelete='cascade',
        así que borrar una raíz arrastra en cascada TODAS las estanterías que cuelgan de ella, y
        cada caja se queda sin posición. Un clic, sin aviso y sin vuelta atrás.

        '_force_unlink' es la marca que pone Odoo al desinstalar un módulo
        (MODULE_UNINSTALL_FLAG en ir_model.py): ahí sí hay que dejar borrar, o la desinstalación
        de leulit_almacen fallaría."""
        if not self._context.get('_force_unlink'):
            raices = self.env['stock.quant.package']._raices_estanterias()
            if raices & self:
                raise UserError(_(
                    'No se puede borrar "%s": es la raíz de las estanterías de una compañía. '
                    'Borrarla eliminaría en cascada todas sus estanterías y dejaría sin posición '
                    'a todas las cajas.') % (raices & self)[0].display_name)
        return super(StockLocation, self).unlink()
