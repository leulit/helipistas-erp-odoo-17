# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
import pyqrcode

_logger = logging.getLogger(__name__)


class StockQuantPackage(models.Model):
    _name = 'stock.quant.package'
    _inherit = 'stock.quant.package'

    _sql_constraints = [
        ('leulit_name_uniq', 'unique(name)',
         'Ya existe una caja con ese código. El código de caja es único en todo el almacén.'),
    ]

    # OJO: estanteria_id NO lleva required=True a nivel de modelo a propósito. El botón nativo
    # "Poner en paquete" (stock.picking.action_put_in_pack) crea paquetes sin estantería y
    # fallaría. La obligatoriedad se impone en la vista formulario, que es donde las personas
    # dan de alta las cajas.
    def _get_qr(self):
        for item in self:
            item.qr = False
            # Formato del QR de caja: "CAJA | id | nombre". El prefijo CAJA lo distingue del QR
            # de pieza, que es "id | codigo" (ver stock_lot._get_qr). La app ICARUS parte la
            # cadena por "|" y hace trim de cada trozo, así que los espacios dan igual.
            if isinstance(item.id, int) and item.name:
                tiraqr = "CAJA | %s | %s" % (item.id, item.name)
                qr = pyqrcode.create(tiraqr, mode='binary')
                item.qr = qr.png_as_base64_str(3)


    @api.model
    def _raices_estanterias(self):
        """Las dos ubicaciones raíz, una por compañía. Se resuelven por xmlid, nunca por nombre:
        se pueden renombrar sin romper nada."""
        raices = self.env['stock.location'].browse()
        for xmlid in ('leulit_almacen.location_estanterias_ica',
                      'leulit_almacen.location_estanterias_hlp'):
            raiz = self.env.ref(xmlid, raise_if_not_found=False)
            if raiz:
                raices |= raiz
        return raices


    def _domain_estanteria(self):
        """Las estanterías reales: las que cuelgan de una de las dos raíces (las raíces en sí no
        son estanterías, solo agrupan). usage='view' es la garantía de que una estantería nunca
        puede contener stock (stock.quant.check_location_id).
        Sin este dominio el desplegable ofrece cualquier ubicación de tipo vista: ICA,
        WH-HELIPISTAS, Partner Locations..."""
        raices = self._raices_estanterias()
        if not raices:
            # No se levanta excepción: esto se evalúa al pintar el formulario de caja y una traza
            # dejaría la pantalla inservible. Desplegable vacío + warning en el log.
            _logger.warning('Faltan las ubicaciones raíz de estanterías (location_estanterias_ica '
                            '/ _hlp): el desplegable de estantería saldrá vacío.')
            return [('id', '=', False)]
        return [('usage', '=', 'view'), ('id', 'child_of', raices.ids), ('id', 'not in', raices.ids)]


    @api.model
    def get_estanterias_app(self):
        """Estanterías donde la app puede colocar una caja. Existe para que la app NO tenga que
        filtrar por nombre: complete_name de una ubicación de tipo 'view' es solo su propio
        nombre, sin la ruta del padre (stock.location._compute_complete_name), así que un dominio
        tipo [('complete_name','like','Estanterias/')] no puede funcionar. Y ir.model.data no es
        legible por un usuario interno, así que la app tampoco puede resolver los xmlid.
        El search_read va con los permisos del usuario: la regla multi-compañía de stock.location
        ya deja fuera las estanterías de la otra compañía."""
        return self.env['stock.location'].search_read(self._domain_estanteria(), ['id', 'name'])


    @api.constrains('estanteria_id', 'company_id')
    def _check_estanteria_company(self):
        """Los almacenes de Icarus y de Helipistas están separados: una caja no puede colocarse
        en una estantería de otra compañía. La regla multi-compañía de stock.location ya oculta
        las estanterías ajenas, pero no impide escribirlas a un usuario con las dos compañías
        activas, ni por XML-RPC desde la app."""
        for item in self:
            estanteria = item.estanteria_id
            if estanteria.company_id and item.company_id and estanteria.company_id != item.company_id:
                raise ValidationError(_(
                    'La estantería "%s" es de %s y la caja es de %s. Los almacenes de las dos '
                    'compañías están separados.') % (
                        estanteria.display_name, estanteria.company_id.name, item.company_id.name))


    qr = fields.Char(compute=_get_qr, store=False, string='QR')
    estanteria_id = fields.Many2one(
        comodel_name='stock.location', string='Estantería',
        domain=lambda self: self._domain_estanteria(), ondelete='restrict',
        help="Estantería física donde está colocada la caja. No tiene nada que ver con la "
             "ubicación del contenido, que representa el estado del material.")
