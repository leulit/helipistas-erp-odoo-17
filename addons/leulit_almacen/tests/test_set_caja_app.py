# -*- encoding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSetCajaApp(TransactionCase):
    """El caso que rompio en produccion: un lote con las existencias partidas en dos filas de
    stock.quant en la MISMA ubicacion, una con propietario y otra sin el. owner_id forma parte
    de la clave de stock.quant, asi que Odoo no las fusiona nunca; la ficha de la pieza las
    suma y ensena el total, y en el almacen esas unidades estan en una sola caja."""

    def setUp(self):
        super().setUp()
        self.ubicacion = self.env['stock.location'].create({
            'name': 'TEST Material Nuevo',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_locations').id,
        })
        self.producto = self.env['product.product'].create({
            'name': 'TEST pieza', 'type': 'product', 'tracking': 'lot',
        })
        self.lote = self.env['stock.lot'].create({
            'name': 'TEST-LOTE-001', 'product_id': self.producto.id,
        })
        self.caja = self.env['stock.quant.package'].create({'name': 'TEST-C-001'})

    def _quant(self, cantidad, propietario=False):
        return self.env['stock.quant'].create({
            'product_id': self.producto.id,
            'location_id': self.ubicacion.id,
            'lot_id': self.lote.id,
            'quantity': cantidad,
            'owner_id': propietario and propietario.id or False,
        })

    def _set_caja(self, caja_id):
        return self.lote.with_context(args={
            'lote_id': self.lote.id,
            'location_id': self.ubicacion.id,
            'caja_id': caja_id,
        }).set_caja_app()

    def test_filas_partidas_por_propietario_van_a_la_misma_caja(self):
        con_propietario = self._quant(5, self.env.ref('base.main_partner'))
        sin_propietario = self._quant(7)
        self._set_caja(self.caja.id)
        self.assertEqual(con_propietario.package_id, self.caja)
        self.assertEqual(sin_propietario.package_id, self.caja)

    def test_filas_negativas_no_cuentan(self):
        positiva = self._quant(5)
        negativa = self._quant(-2, self.env.ref('base.main_partner'))
        self._set_caja(self.caja.id)
        self.assertEqual(positiva.package_id, self.caja)
        self.assertFalse(negativa.package_id)

    def test_reparto_fisico_real_sigue_fallando(self):
        otra_caja = self.env['stock.quant.package'].create({'name': 'TEST-C-002'})
        self._quant(5).package_id = self.caja
        self._quant(7).package_id = otra_caja
        with self.assertRaises(UserError):
            self._set_caja(self.caja.id)
