# -*- encoding: utf-8 -*-
from datetime import timedelta
from odoo import fields
from odoo.tests import common, tagged
from odoo.exceptions import UserError, AccessError


@tagged('post_install', '-at_install')
class TestPartePrivado(common.TransactionCase):

    def setUp(self):
        super().setUp()
        grupo = self.env.ref('leulit.ROperaciones_parte_privado')
        self.operador = self.env['res.users'].create({
            'name'      : 'Operador parte privado',
            'login'     : 'operador_parte_privado_test',
            'groups_id' : [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('leulit.RBase').id, grupo.id])],
        })
        self.Wizard = self.env['leulit.parte.privado.wizard'].with_user(self.operador)

    def test_sin_grupo_no_accede(self):
        sin_grupo = self.env['res.users'].create({'name': 'Sin grupo', 'login': 'sin_grupo_parte_privado_test', 'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]})
        with self.assertRaises(AccessError):
            self.env['leulit.parte.privado.wizard'].with_user(sin_grupo).check_access_rights('create')

    def test_piloto_sin_usuario(self):
        partner = self.env['res.partner'].new({'name': 'Piloto sin usuario'})
        piloto = self.env['leulit.piloto'].new({'partner_id': partner.id, 'privado': True})
        wiz = self.Wizard.new({'piloto_id': piloto.id})
        with self.assertRaises(UserError):
            wiz._usuario_piloto()

    def _datos_reales(self):
        """Datos maestros de la BD de pruebas; None si faltan (el test se salta)."""
        Vuelo = self.env['leulit.vuelo']
        piloto = self.env['leulit.piloto'].search([('privado','=',True),('partner_id.user_ids.active','=',True)], limit=1)
        presupuesto = self.env['sale.order'].search([('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)], limit=1)
        tipo = self.env['leulit.vuelostipo'].search([('tipo_trabajo','=','NCO')], limit=1)
        helipuerto = self.env['leulit.helipuerto'].search([], limit=1)
        heli = False
        for h in self.env['leulit.helicoptero'].search([('baja','=',False),('statemachine','=','En servicio')]):
            if h.horas_remanente > 2 and h.consumomedio > 0 and h.velocidad > 0 and not Vuelo.search([('helicoptero_id','=',h.id),('estado','=','prevuelo')], limit=1):
                heli = h
                break
        if not (piloto and presupuesto and tipo and helipuerto and heli):
            return None
        ultimo = Vuelo.search([('helicoptero_id','=',heli.id),('estado','in',['postvuelo','cerrado'])], order='fechasalida desc', limit=1)
        fecha = (ultimo.fechavuelo if ultimo else fields.Date.today()) + timedelta(days=1)
        objetivo_fuel = 300 if heli.tipo == 'EC120B' else 100
        return {
            'fechavuelo'      : fecha,
            'helicoptero_id'  : heli.id,
            'piloto_id'       : piloto.id,
            'presupuesto_vuelo': presupuesto.id,
            'vuelo_tipo_id'   : tipo.id,
            'numpax'          : 0,
            'lugarsalida'     : helipuerto.id,
            'lugarllegada'    : helipuerto.id,
            'horasalida'      : 10.0,
            'tiemposervicio'  : 1.0,
            'fuelqty'         : max(0.0, objetivo_fuel - (ultimo.fuelllegada if ultimo else 0.0)),
            'tacomllegada'    : (ultimo.tacomllegada if ultimo else 0.0) + 1.0,
            'ngvuelo'         : 1.0,
            'nfvuelo'         : 1.0,
            'declaracion'     : True,
        }

    def test_flujo_completo(self):
        datos = self._datos_reales()
        if not datos:
            self.skipTest('faltan datos maestros: piloto privado con usuario activo, helicóptero en servicio con potencial, presupuesto NCO en sale, tipo de vuelo NCO, helipuerto')
        Vuelo = self.env['leulit.vuelo']

        # 1) fallo tardío (cadena B: tacómetro/NG de llegada 0) -> UserError y vuelo cancelado, no bloquea
        es_ec120b = self.env['leulit.helicoptero'].browse(datos['helicoptero_id']).tipo == 'EC120B'
        with self.assertRaises(UserError):
            self.Wizard.create(dict(datos, ngvuelo=0.0) if es_ec120b else dict(datos, tacomllegada=0.0)).finalizar()
        fallido = Vuelo.search([('privado_introducido_por','=',self.operador.id)])
        self.assertTrue(all(v.estado == 'cancelado' for v in fallido))

        # 2) ciclo feliz
        self.Wizard.create(datos).finalizar()
        vuelo = Vuelo.search([('privado_introducido_por','=',self.operador.id),('estado','=','cerrado')])
        self.assertEqual(len(vuelo), 1)
        self.assertEqual(vuelo.control_firma, 'firmado')
        self.assertEqual(vuelo.tipo_actividad, 'NCO')
        self.assertEqual(vuelo.lugarsalida.id, datos['lugarsalida'])
        self.assertEqual(vuelo.create_uid.partner_id, vuelo.piloto_id.partner_id)
        docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.vuelo'),('idmodelo','=',vuelo.id)])
        self.assertTrue(any(d.referencia.endswith('-POV') for d in docs))
        self.assertTrue(any(d.referencia.endswith('-PTV') for d in docs))
        self.assertTrue(all(d.firmado_por == vuelo.piloto_id.partner_id for d in docs))
        self.assertTrue(any('Parte piloto privado' in (m.body or '') for m in vuelo.message_ids))
