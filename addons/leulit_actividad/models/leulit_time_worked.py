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


class leulit_time_worked(models.Model):
    _name             = "leulit.time_worked"
    _description    = "leulit_time_worked"
    

    def _get_horas_total(self):
        for item in self:
            cont = 0
            cont = item.horas_enero + item.horas_febrero + item.horas_marzo + item.horas_abril + item.horas_mayo + item.horas_junio + item.horas_julio + item.horas_agosto + item.horas_septiembre + item.horas_octubre + item.horas_noviembre + item.horas_diciembre
            item.horas_total = cont
    

    def _get_horas_enero(self):
        for item in self:
            mes = '01'
            df = '31'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_febrero(self):
        for item in self:
            mes = '02'
            df=0
            if item.year%4 == 0:
                df = '29'
            else:
                df = '28'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_marzo(self):
        for item in self:
            mes = '03'
            df = '31'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_abril(self):
        for item in self:
            mes = '04'
            df = '30'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_mayo(self):
        for item in self:
            mes = '05'
            df = '31'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_junio(self):
        for item in self:
            mes = '06'
            df = '30'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_julio(self):
        for item in self:
            mes = '07'
            df = '31'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_agosto(self):
        for item in self:
            mes = '08'
            df = '31'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_septiembre(self):
        for item in self:
            mes = '09'
            df = '30'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_octubre(self):
        for item in self:
            mes = '10'
            df = '31'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_noviembre(self):
        for item in self:
            mes = '11'
            df = '30'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)

    def _get_horas_diciembre(self):
        for item in self:
            mes = '12'
            df = '31'
            y = str(item.year)
            fecha_inicial = y+'-'+mes+'-01'
            fecha_fin = y+'-'+mes+'-'+df
            item.get_horas_mensual(fecha_inicial,fecha_fin)


    
    def _get_horas_mensual(self, fecha_inicial, fecha_fin):
        total = 0.0
        piloto = self.env['leulit.piloto'].search([('id','=',self.partner.getPiloto())])
        profesor = self.env['leulit.profesor'].search([('id','=',self.partner.getProfesor())])
        operador = self.env['leulit.operador'].search([('id','=',self.partner.getOperador())])
        dates = []
        timedates = {}
        #PILOTO
        if piloto:
            # TAREAS -> TODO
            tareas = self.env['leulit.piloto_tarea'].search([('partner','=',piloto.getPartnerId()),('fecha', '<=', fecha_fin),('fecha', '>=', fecha_inicial),('vuelo_id','=',False)], order="fecha desc")
            for tarea in tareas:
                if tarea.fecha not in dates:
                    dates.append(tarea.fecha)
                    timedates[tarea.fecha] = tarea.tiempo
                else:
                    timedates[tarea.fecha] = timedates[tarea.fecha] + tarea.tiempo
            # VUELOS -> BUSCAMOS TODOS LOS VUELOS PIC O OPERADOR 
            # TODO El operador siguiente ha de ser el campo "operador"(leulit.operador) y no el campo "operador_id"(leulit.piloto)
            vuelos = self.env['leulit.vuelo'].search([('fechavuelo', '<=', fecha_fin),('fechavuelo', '>=', fecha_inicial),('estado','=','cerrado'),'|',('piloto_id','=',piloto.id),('operador','=',operador.id)], order="fechavuelo desc, horasalida desc")
            nextvuelo = False
            fechavuelos = []
            for vuelo in vuelos:
                if vuelo.fechavuelo in fechavuelos:
                    if nextvuelo.horasalida - vuelo.horallegada < 3:
                        if vuelo.fechavuelo not in dates:
                            dates.append(vuelo.fechavuelo)
                            timedates[vuelo.fechavuelo] = vuelo.airtime + (nextvuelo.horasalida - vuelo.horallegada)
                        else:
                            timedates[vuelo.fechavuelo] = timedates[vuelo.fechavuelo] + vuelo.airtime + (nextvuelo.horasalida - vuelo.horallegada)
                    else:
                        if vuelo.fechavuelo not in dates:
                            dates.append(vuelo.fechavuelo)
                            timedates[vuelo.fechavuelo] = 0.75 + vuelo.airtime + 0.5
                        else:
                            timedates[vuelo.fechavuelo] = timedates[vuelo.fechavuelo] + 0.75 + vuelo.airtime + 0.5
                    nextvuelo = vuelo
                else:
                    fechavuelos.append(vuelo.fechavuelo)
                    if vuelo.fechavuelo not in dates:
                        dates.append(vuelo.fechavuelo)
                        timedates[vuelo.fechavuelo] = 0.75 + vuelo.airtime + 0.5
                    else:
                        timedates[vuelo.fechavuelo] = timedates[vuelo.fechavuelo] + 0.75 + vuelo.airtime + 0.5
                    nextvuelo = vuelo
            # PARTES ESCUELA -> BUSCAMOS TODOS
            partes_escuela = self.env['leulit.parte_escuela'].search([('fecha', '<=', fecha_fin),('fecha', '>=', fecha_inicial),('estado','=','cerrado'),('vuelo_id','=',False),('profesor','=',profesor.id)], order="fecha desc")
            for parte in partes_escuela:
                if parte.fecha not in dates:
                    dates.append(parte.fecha)
                    timedates[parte.fecha] = parte.tiempo
                else:
                    timedates[parte.fecha] = timedates[parte.fecha] + parte.tiempo
        else:
            #TAREAS GENERALES HLP
            tareas = self.env['leulit.tarea_tiempo'].search([('partner','=',self.partner.id),('fecha', '<=', fecha_fin),('fecha', '>=', fecha_inicial)], order="fecha desc")
            for tarea in tareas:
                if tarea.fecha not in dates:
                    dates.append(tarea.fecha)
                    timedates[tarea.fecha] = tarea.tiempo
                else:
                    timedates[tarea.fecha] = timedates[tarea.fecha] + tarea.tiempo
        
        for date in dates:
            if timedates[date] > 12:
                total = total + 12
            else:
                total = total + timedates[date]
        return total

    year = fields.Integer(string='Año')
    partner = fields.Many2one(comodel_name='res.partner', string='Partner')
    horas_enero = fields.Float(compute='_get_horas_enero',string='Enero',store=False)
    horas_febrero = fields.Float(compute='_get_horas_febrero',string='Enero',store=False)
    horas_marzo = fields.Float(compute='_get_horas_marzo',string='Enero',store=False)
    horas_abril = fields.Float(compute='_get_horas_abril',string='Enero',store=False)
    horas_mayo = fields.Float(compute='_get_horas_mayo',string='Enero',store=False)
    horas_junio = fields.Float(compute='_get_horas_junio',string='Enero',store=False)
    horas_julio = fields.Float(compute='_get_horas_julio',string='Enero',store=False)
    horas_agosto = fields.Float(compute='_get_horas_agosto',string='Enero',store=False)
    horas_septiembre = fields.Float(compute='_get_horas_septiembre',string='Enero',store=False)
    horas_octubre = fields.Float(compute='_get_horas_octubre',string='Enero',store=False)
    horas_noviembre = fields.Float(compute='_get_horas_noviembre',string='Enero',store=False)
    horas_diciembre = fields.Float(compute='_get_horas_diciembre',string='Enero',store=False)
    horas_total = fields.Float(compute='_get_horas_total',string='Total',store=False)
