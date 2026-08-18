# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = 'stock.location'

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
