# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class leulitCtrlCombustiblePunto(models.Model):
    _name = "leulit.ctrl_combustible_punto"
    _order = "sequence"

    @api.depends('control_totalizador','gestion_propia')
    def get_last_totalizador(self):
        for item in self:
            item.last_totalizador_avgas = 0
            item.last_totalizador_jeta = 0
            if item.control_totalizador and item.gestion_propia:
                if item.avgas:
                    last_ctrl = self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'AV-Gas')], order='fecha DESC, hora DESC', limit=1)
                    if last_ctrl:
                        item.last_totalizador_avgas = last_ctrl.totalizador
                if item.jeta:
                    last_ctrl = self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'Jeta')], order='fecha DESC, hora DESC', limit=1)
                    if last_ctrl:
                        item.last_totalizador_jeta = last_ctrl.totalizador

    @api.depends('gestion_propia')
    def ctrl_cantidad(self):
        for item in self:
            item.cantidad_ctrl_avgas = 0
            item.cantidad_ctrl_jeta = 0
            if item.gestion_propia:
                if item.avgas:
                    for ctrl in self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'AV-Gas')]):
                        if ctrl.from_punto == item.id:
                            item.cantidad_ctrl_avgas = -ctrl.cantidad
                        else:
                            item.cantidad_ctrl_avgas = ctrl.cantidad
                if item.jeta:
                    for ctrl in self.env['leulit.ctrl_combustible'].search(['|',('from_punto', '=', item.id),('to_punto', '=', item.id),('tipo', '=', 'Jeta')]):
                        if ctrl.from_punto == item.id:
                            item.cantidad_ctrl_jeta = -ctrl.cantidad
                        else:
                            item.cantidad_ctrl_jeta = ctrl.cantidad

    @api.depends('gestion_propia','control_totalizador','last_totalizador_avgas','last_totalizador_jeta')
    def ctrl_cantidad_totalizador(self):
        for item in self:
            item.cantidad_ctrl_totalizador_avgas = 0
            item.cantidad_ctrl_totalizador_jeta = 0
            if item.control_totalizador and  item.gestion_propia:
                if item.avgas:
                    cantidad = 0
                    for ctrl in self.env['leulit.ctrl_combustible'].search([('to_punto', '=', item.id),('fecha', '>=', item.fecha_inicial_avgas),('tipo', '=', 'AV-Gas')]):
                        cantidad += ctrl.cantidad
                    cantidad += item.cantidad_inicial_avgas
                    item.cantidad_ctrl_totalizador_avgas = item.totalizador_inicial_avgas + cantidad - item.last_totalizador_avgas
                if item.jeta:
                    cantidad = 0
                    for ctrl in self.env['leulit.ctrl_combustible'].search([('to_punto', '=', item.id),('fecha', '>=', item.fecha_inicial_avgas),('tipo', '=', 'Jeta')]):
                        cantidad += ctrl.cantidad
                    cantidad += item.cantidad_inicial_jeta
                    item.cantidad_ctrl_totalizador_jeta = item.totalizador_inicial_jeta + cantidad - item.last_totalizador_jeta

    name = fields.Char(string="Nombre", required=True, translate=True)
    sequence = fields.Integer(string="Secuencia", default=1)
    control_totalizador = fields.Boolean(string="Control Totalizador")
    flag_otro = fields.Boolean(string="Otros")
    gestion_propia = fields.Boolean(string="Gestion Propia")
    aviso_avgas = fields.Float(string="Aviso Avgas", help="Cantidad de combustible que se considera aviso para el punto de combustible")
    aviso_jeta = fields.Float(string="Aviso JetA1", help="Cantidad de combustible que se considera aviso para el punto de combustible")
    # Campos para determinar si el punto tiene avgas y/o jeta
    avgas = fields.Boolean(string="AV-GAS")
    jeta = fields.Boolean(string="Jet-A1")
    # Campos de inicializacion del punto con combustible AV-GAS
    cantidad_inicial_avgas = fields.Float(string="Cantidad Inicial AV-GAS")
    totalizador_inicial_avgas = fields.Float(string="Totalizador Inicial AV-GAS")
    fecha_inicial_avgas = fields.Date(string="Fecha Inicial AV-GAS")
    # Campos calculados para tener el totalizador y la cantidad de combustible actual
    last_totalizador_avgas = fields.Float(string="Ultimo Totalizador AV-GAS", compute="get_last_totalizador", store=False)
    cantidad_ctrl_avgas = fields.Float(string="Cantidad AV-GAS", compute="ctrl_cantidad", store=False)
    cantidad_ctrl_totalizador_avgas = fields.Float(string="Cantidad AV-GAS", compute="ctrl_cantidad_totalizador", store=False)
    # Campos de inicializacion del punto con combustible Jet-A1
    cantidad_inicial_jeta = fields.Float(string="Cantidad Inicial Jet-A1")
    totalizador_inicial_jeta = fields.Float(string="Totalizador Inicial Jet-A1")
    fecha_inicial_jeta = fields.Date(string="Fecha Inicial Jet-A1")
    # Campos calculados para tener el totalizador y la cantidad de combustible actual
    last_totalizador_jeta = fields.Float(string="Ultimo Totalizador Jet-A1", compute="get_last_totalizador", store=False)
    cantidad_ctrl_jeta = fields.Float(string="Cantidad Jet-A1", compute="ctrl_cantidad", store=False)
    cantidad_ctrl_totalizador_jeta = fields.Float(string="Cantidad Jet-A1", compute="ctrl_cantidad_totalizador", store=False)


    def cron_aviso_combustible(self):
        _logger.error("cron_aviso_combustible")
        context = self.env.context.copy()
        puntos = self.search([('gestion_propia', '=', True)])
        for punto in puntos:
            mensajes = []

            # --- Control AV-GAS ---
            if punto.avgas:
                cantidad_avgas = 0
                if punto.gestion_propia:
                    if punto.control_totalizador:
                        cantidad_avgas = punto.cantidad_ctrl_totalizador_avgas
                    else:
                        cantidad_avgas = punto.cantidad_ctrl_avgas

                    if cantidad_avgas < punto.aviso_avgas:
                        mensajes.append(f"AV-GAS en '{punto.name}' bajo aviso: {cantidad_avgas:.2f} L (umbral: {punto.aviso_avgas:.2f} L)")

            # --- Control JET-A1 ---
            if punto.jeta:
                cantidad_jeta = 0
                if punto.gestion_propia:
                    if punto.control_totalizador:
                        cantidad_jeta = punto.cantidad_ctrl_totalizador_jeta
                    else:
                        cantidad_jeta = punto.cantidad_ctrl_jeta

                    if cantidad_jeta < punto.aviso_jeta:
                        mensajes.append(f"JET-A1 en '{punto.name}' bajo aviso: {cantidad_jeta:.2f} L (umbral: {punto.aviso_jeta:.2f} L)")
            
            # Si hay avisos, enviar mail con plantilla
            if mensajes:
                body = "<br/>".join(mensajes)
                try:
                    template = self.env.ref('leulit_combustible.leulit_aviso_combustible')
                    template.with_context(
                        body=body,
                        punto=punto,
                    ).send_mail(punto.id, force_send=True)
                except Exception as e:
                    _logger.error(f"Error al enviar aviso de combustible: {str(e)}")