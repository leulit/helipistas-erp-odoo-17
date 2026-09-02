# -*- encoding: utf-8 -*-
from odoo import models, fields, _
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
    numpax = fields.Integer('Nº de pax / AESA', default=0)
    numpae = fields.Integer('Num. AL/PA/PE/PAE/PO', required=True)
    lugarsalida = fields.Many2one('leulit.helipuerto', 'Helipuerto salida', required=True)
    lugarllegada = fields.Many2one('leulit.helipuerto', 'Helipuerto llegada', required=True)
    horasalida = fields.Float('Hora salida local', required=True)
    horallegada = fields.Float('Hora llegada local', required=True)
    tiemposervicio = fields.Float('Tiempo servicio', required=True)
    airtime = fields.Float('Air Time', required=True)
    fuelqty = fields.Float('Combustible añadido (l.)')
    oilqty = fields.Float('Aceite añadido (l.)')
    fuelllegada = fields.Float('Combustible llegada (l.)', required=True)
    tacomllegada = fields.Float('Tacom. llegada')
    ngvuelo = fields.Float('NG vuelo')
    nfvuelo = fields.Float('NF vuelo')
    comentarios = fields.Text('Observaciones (O.V.)')
    declaracion = fields.Boolean('Inspección prevuelo, briefing, NOTAM y debriefing realizados')

    def _usuario_piloto(self):
        user = self.piloto_id.partner_id.user_ids.filtered('active')[:1]
        if not user:
            raise UserError(_("El piloto %s no tiene usuario activo en el ERP; no se puede firmar en su nombre.") % self.piloto_id.name)
        return user

    def _vals_vuelo(self, hay_vuelo_anterior):
        tiempoprevisto = self.horallegada - self.horasalida
        if tiempoprevisto < 0:
            tiempoprevisto += 24.0
        return {
            'fechavuelo'                     : self.fechavuelo,
            'helicoptero_id'                 : self.helicoptero_id.id,
            'piloto_id'                      : self.piloto_id.id,
            'presupuesto_vuelo'              : self.presupuesto_vuelo.id,
            'vuelo_tipo_line'                : [(0, 0, {'vuelo_tipo_id': self.vuelo_tipo_id.id})],
            'numpax'                         : self.numpax,
            'numpae'                         : self.numpae,
            'lugarsalida'                    : self.lugarsalida.id,
            'lugarllegada'                   : self.lugarllegada.id,
            'horasalida'                     : self.horasalida,
            'horallegada'                    : self.horallegada,
            'tiempoprevisto'                 : round(tiempoprevisto, 2),
            'tiemposervicio'                 : self.tiemposervicio,
            'airtime'                        : self.airtime,
            'fuelqty'                        : self.fuelqty,
            'oilqty'                         : self.oilqty,
            'fuelllegada'                    : self.fuelllegada,
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
        user = self._usuario_piloto()
        user.sudo().get_otp_secret()
        Vuelo = self.env['leulit.vuelo'].with_user(user)
        hay_anterior = bool(Vuelo.search([('helicoptero_id','=',self.helicoptero_id.id),('estado','=','cerrado'),('fechavuelo','=',self.fechavuelo),('horasalida','<',self.horasalida)], limit=1))
        vuelo = Vuelo.create(self._vals_vuelo(hay_anterior))
        try:
            vuelo.onchange_helicoptero()                          # pesos, velocidad, consumo, tacom/fuel del último vuelo cerrado
            vuelo.write({'lugarsalida': self.lugarsalida.id})     # el onchange lo pisa con la llegada del vuelo anterior
            vuelo.calculosFuel('tiempoprevisto')                  # distancia, hora llegada prevista, combustibles
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
