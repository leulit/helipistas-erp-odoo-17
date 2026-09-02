# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.leulit_operaciones import vuelo_chain_postvuelo, vuelo_chain_cerrado
from ..chains import vuelo_chain_privado

import logging
_logger = logging.getLogger(__name__)


class PartePrivadoWizard(models.TransientModel):
    _name = "leulit.parte.privado.wizard"
    _description = "Parte piloto privado"

    fechavuelo = fields.Date('Fecha', required=True, default=fields.Date.context_today)
    helicoptero_id = fields.Many2one('leulit.helicoptero', 'Helicóptero', required=True, domain="[('baja','=',False)]")
    helicoptero_tipo = fields.Selection(related='helicoptero_id.tipo')
    piloto_id = fields.Many2one('leulit.piloto', 'Piloto', required=True, domain="[('privado','=',True)]")
    presupuesto_vuelo = fields.Many2one('sale.order', 'Presupuesto', required=True, domain=[('flag_flight_part','=',True),('state','=','sale'),('task_done','=',False)])
    vuelo_tipo_id = fields.Many2one('leulit.vuelostipo', 'Tipo vuelo', required=True, domain="[('tipo_trabajo','=','NCO')]")
    numpax = fields.Integer('Nº de pax / AESA', default=1)
    lugarsalida = fields.Many2one('leulit.helipuerto', 'Helipuerto salida', required=True)
    lugarllegada = fields.Many2one('leulit.helipuerto', 'Helipuerto llegada', required=True)
    horasalida = fields.Float('Hora salida local', required=True)
    tiemposervicio = fields.Float('Tiempo servicio', required=True)
    horallegada = fields.Float('Hora llegada local', compute='_compute_horas')
    airtime = fields.Float('Air Time', compute='_compute_horas')
    fuelqty = fields.Float('Combustible añadido (l.)')
    fuel_remanente = fields.Float('Remanente último vuelo (l.)', compute='_compute_fuel')
    fuel_minimo = fields.Float('Combustible mínimo (l.)', compute='_compute_fuel')
    fuel_insuficiente = fields.Boolean(compute='_compute_fuel')
    tacomllegada = fields.Float('Tacom. llegada')
    ngvuelo = fields.Float('NG vuelo')
    nfvuelo = fields.Float('NF vuelo')
    comentarios = fields.Text('Observaciones (O.V.)')
    declaracion = fields.Boolean('Inspección prevuelo, briefing, NOTAM y debriefing realizados')

    @api.depends('horasalida', 'tiemposervicio')
    def _compute_horas(self):
        for w in self:
            llegada = w.horasalida + w.tiemposervicio
            w.horallegada = llegada - 24.0 if llegada >= 24.0 else llegada
            w.airtime = max(w.tiemposervicio - 0.1, 0.0)    # servicio - 6 min exactos (la constraint de múltiplo de 6 min se exime en models/leulit_vuelo.py)

    @api.depends('helicoptero_id', 'tiemposervicio')
    def _compute_fuel(self):
        # Mismo remanente que usa onchange_helicoptero y misma fórmula de mínimo que calculosFuel (reserva 30 min)
        Vuelo = self.env['leulit.vuelo']
        for w in self:
            ultimo = Vuelo.search([('helicoptero_id','=',w.helicoptero_id.id),('estado','=','cerrado'),('fechasalida','!=',False)], limit=1, order='fechasalida desc')
            w.fuel_remanente = ultimo.fuelllegada
            w.fuel_minimo = Vuelo._calc_combustible_minimo(w.tiemposervicio, '30', w.helicoptero_id.consumomedio, '0', '0', 0, w.helicoptero_id.velocidad) if w.helicoptero_id else 0.0
            w.fuel_insuficiente = bool(w.helicoptero_id) and w.fuel_remanente < w.fuel_minimo

    def _usuario_piloto(self):
        user = self.piloto_id.partner_id.user_ids.filtered('active')[:1]
        if not user:
            raise UserError(_("El piloto %s no tiene usuario activo en el ERP; no se puede firmar en su nombre.") % self.piloto_id.name)
        return user

    def _vals_vuelo(self, hay_vuelo_anterior):
        return {
            'fechavuelo'                     : self.fechavuelo,
            'helicoptero_id'                 : self.helicoptero_id.id,
            'piloto_id'                      : self.piloto_id.id,
            'presupuesto_vuelo'              : self.presupuesto_vuelo.id,
            'vuelo_tipo_line'                : [(0, 0, {'vuelo_tipo_id': self.vuelo_tipo_id.id})],
            'numpax'                         : self.numpax,
            'numpae'                         : 0,
            'lugarsalida'                    : self.lugarsalida.id,
            'lugarllegada'                   : self.lugarllegada.id,
            'horasalida'                     : self.horasalida,
            'horallegada'                    : self.horallegada,
            'tiempoprevisto'                 : self.tiemposervicio,
            'tiemposervicio'                 : self.tiemposervicio,
            'airtime'                        : self.airtime,
            'fuelqty'                        : self.fuelqty,
            'oilqty'                         : 0.0,
            'tacomllegada'                   : self.tacomllegada,
            'ngvuelo'                        : self.ngvuelo,
            'nfvuelo'                        : self.nfvuelo,
            'comentarios'                    : self.comentarios,
            'checklist_realizado'            : True,
            'briefing_realizado'             : True,
            'notam_revisado'                 : True,
            'checklist_postvuelo_realizado'  : True,
            'checklist_prevuelo_BFF'         : not hay_vuelo_anterior,
            'checklist_prevuelo_entre_vuelos': hay_vuelo_anterior,
            # constantes spec §4.4; el resto (nightlandings, arlanding, sling_cycle, ifr, nv, balsa,
            # flotadores, chalecos, uso_gancho, distancia_alternativo) ya son los defaults del modelo
            'numtripulacion'                 : 1,
            'asiento_pic'                    : 'pic_right',
            'reservasfuel'                   : '30',
            'rodaje'                         : '0',
            'contingencia'                   : '0',
            'landings'                       : 1,
            'privado_introducido_por'        : self.env.user.id,
        }

    @staticmethod
    def _ejecutar(chain, request, vuelo):
        request.env = vuelo.env
        request.vuelo_id = vuelo.id
        request.uid = vuelo.env.uid
        request.tipo_helicoptero = vuelo.helicoptero_id.modelo.tipo
        chain.handle(request)

    @staticmethod
    def _firmar(vuelo):
        # Equivale a leulit_signaturedoc.checksignatureRef con el OTP real del piloto (env.user = piloto)
        otp = vuelo.env.user.get_otp()
        esignature = vuelo.env['leulit_signaturedoc'].buildSignature('leulit.vuelo', vuelo.id, otp)
        vuelo.buildPdfSigned(None, esignature)

    def finalizar(self):
        self.ensure_one()
        if not self.declaracion:
            raise UserError(_("Debe confirmar la declaración de inspección prevuelo, briefing, NOTAM y debriefing."))
        if self.fuel_remanente + self.fuelqty < self.fuel_minimo:
            raise UserError(_("Combustible de salida insuficiente: remanente %.0f l. + añadido %.0f l. es menor que el mínimo %.0f l. Indique el combustible añadido según el PTV.") % (self.fuel_remanente, self.fuelqty, self.fuel_minimo))
        user = self._usuario_piloto()
        user.sudo().get_otp_secret()
        Vuelo = self.env['leulit.vuelo'].with_user(user)
        hay_anterior = bool(Vuelo.search([('helicoptero_id','=',self.helicoptero_id.id),('estado','=','cerrado'),('fechavuelo','=',self.fechavuelo),('horasalida','<',self.horasalida)], limit=1))
        vuelo = Vuelo.create(self._vals_vuelo(hay_anterior))
        try:
            vuelo.onchange_helicoptero()                          # pesos, velocidad, consumo, tacom/fuel del último vuelo cerrado
            vuelo.write({'lugarsalida': self.lugarsalida.id})     # el onchange lo pisa con la llegada del vuelo anterior
            vuelo.calculosFuel('tiempoprevisto')                  # distancia, hora llegada prevista, combustibles
            vuelo.write({'fuelllegada': vuelo._calc_fuelllegada(vuelo.tiemposervicio, vuelo.fuelsalida, vuelo.consumomedio_vuelo)})  # llegada estimada, no se transcribe
            self._ejecutar(vuelo_chain_privado.chain_to_postvuelo(), vuelo_chain_postvuelo.VueloChainToPostvueloRequest(), vuelo)
            self._firmar(vuelo)                                   # prevuelo -> postvuelo, POV/PTV (+F27 si EC120B con BFF)
            self._ejecutar(vuelo_chain_privado.chain_to_cerrado(), vuelo_chain_cerrado.VueloChainToCerradoRequest(), vuelo)
            if not vuelo.verificar_actividad_aerea(vuelo.fechavuelo, vuelo.piloto_id.partner_id):
                raise UserError(_("No se puede firmar el parte de vuelo porque se ha excedido el tiempo máximo de actividad aérea. Debe crear una ocurrencia para gestionar el exceso de tiempo de actividad aérea."))
            self._firmar(vuelo)                                   # postvuelo -> cerrado, control_firma = firmado
        except Exception as e:
            # ponytail: los handlers hacen cr.commit(), no hay rollback total sin editarlos (invariante spec §2).
            # Se vuelve al último commit y el vuelo queda cancelado para no bloquear helicóptero/piloto.
            self.env.cr.rollback()
            self.env.invalidate_all()
            if vuelo.exists() and vuelo.estado != 'cerrado':
                vuelo.sudo().write({'estado': 'cancelado', 'comentarios': 'Parte piloto privado fallido: %s' % e})
                self.env.cr.commit()
            raise
        vuelo.with_env(self.env).message_post(body=_("Parte introducido por %s mediante Parte piloto privado en nombre de %s") % (self.env.user.name, self.piloto_id.name))
        return {'type': 'ir.actions.act_window_close'}
