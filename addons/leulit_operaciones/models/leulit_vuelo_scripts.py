# -*- encoding: utf-8 -*-
from odoo.addons.leulit import utilitylib
from odoo import models, fields, api, registry, _
import logging
from datetime import timedelta
import threading
_logger = logging.getLogger(__name__)

from datetime import datetime, date, timedelta


class leulitVueloScripts(models.Model):
    _name           = "leulit.vuelo_scripts"
    _description    = "leulit_vuelo_scripts"

    def firmar_cerrar_vuelo(self,idvuelo):
        _logger.error("################### firmar_cerrar_vuelo ")
        threaded_calculation = threading.Thread(target=self.run_firmar_cerrar_vuelo, args=([idvuelo]))
        _logger.error("################### firmar_cerrar_vuelo start thread")
        threaded_calculation.start()

    def run_firmar_cerrar_vuelo(self,idvuelo):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            context = dict(env.context)
            vuelos = env['leulit.vuelo'].with_context(context).sudo().search([('id','=',idvuelo)])
            for vuelo in vuelos:
                args={'otp':'654321',
                      'notp':'654321',
                      'modelo':'leulit.vuelo',
                      'idmodelo':vuelo.id}
                context['args']=args
                if vuelo.piloto_supervisor_id:
                    user = env['res.users'].with_context(context).sudo().search([('partner_id','=',vuelo.piloto_supervisor_id.partner_id.id)])
                else:
                    user = env['res.users'].with_context(context).sudo().search([('partner_id','=',vuelo.piloto_id.partner_id.id)])
                if user:
                    env['leulit_signaturedoc'].with_context(context).sudo().with_user(user.id).checksignatureRef()
                    new_cr.commit()
                    vuelo.write({'estado':'cerrado'})
                    new_cr.commit()
        _logger.error('################### firmar_cerrar_vuelo fin thread')


    def firmar_postvuelo_vuelo(self,idvuelo):
        _logger.error("################### firmar_postvuelo_vuelo ")
        threaded_calculation = threading.Thread(target=self.run_firmar_postvuelo_vuelo, args=([idvuelo]))
        _logger.error("################### firmar_postvuelo_vuelo start thread")
        threaded_calculation.start()

    def run_firmar_postvuelo_vuelo(self,idvuelo):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            context = dict(env.context)
            vuelos = env['leulit.vuelo'].with_context(context).sudo().search([('id','=',idvuelo)])
            for vuelo in vuelos:
                args={'otp':'123456',
                      'notp':'123456',
                      'modelo':'leulit.vuelo',
                      'idmodelo':vuelo.id}
                context['args']=args
                if vuelo.piloto_supervisor_id:
                    user = env['res.users'].with_context(context).sudo().search([('partner_id','=',vuelo.piloto_supervisor_id.partner_id.id)])
                else:
                    user = env['res.users'].with_context(context).sudo().search([('partner_id','=',vuelo.piloto_id.partner_id.id)])
                if user:
                    env['leulit_signaturedoc'].with_context(context).sudo().with_user(user.id).checksignatureRef()
                    new_cr.commit()
                    vuelo.write({'estado':'postvuelo'})
                    new_cr.commit()
        _logger.error('################### firmar_postvuelo_vuelo fin thread')


    def set_create_vuelo(self):
        _logger.error("################### set_create_vuelo ")
        threaded_calculation = threading.Thread(target=self.run_set_create_vuelo, args=([]))
        _logger.error("################### set_create_vuelo start thread")
        threaded_calculation.start()

    def run_set_create_vuelo(self):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            context = dict(env.context)
            datos = {
                'fechavuelo':'2023-01-01',
                'horasalida':10,
                'tiempoprevisto':1,
                'helicoptero_id':4,
                'velocidadprevista':110,
                'distanciatotalprevista':110,
                'presupuesto_vuelo':255,
                'checklist_realizado':True,
                'briefing_realizado':True,
                'lugarsalida':2,
                'lugarllegada':2,
                'piloto_id':17,
                'oilqty':0,
                'fuelqty':120,
                'consumomedio_vuelo':1.92,
                'combustibletrayecto':115.20,
                'combustibleminimo':172.80,
                'editfuelrem':100,
                'fuelsalida':220,
                'combustiblelanding':104.80,
                'combustibleextra':47.20,
                'indicativometeo':'leul',
                'control_firma':'pendiente',
            }
            vuelo = env['leulit.vuelo'].with_context(context).create(datos)
            new_cr.commit()
            vuelo.calculosFuel('velocidadprevista')
            new_cr.commit()
            vuelo.action_obtener_meteo_salida()
            vuelo.getNotam()
            new_cr.commit()

            env['leulit.vuelo_tipo_line'].with_context(context).create({'vuelo_tipo_id':139,'vuelo_id':vuelo.id})
            new_cr.commit()
            
        _logger.error('################### set_create_vuelo fin thread')



    def set_unlink_vuelo(self):
        _logger.error("################### set_unlink_vuelo ")
        threaded_calculation = threading.Thread(target=self.run_set_unlink_vuelo, args=([]))
        _logger.error("################### set_unlink_vuelo start thread")
        threaded_calculation.start()

    def run_set_unlink_vuelo(self):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            context = dict(env.context)
            vuelos = env['leulit.vuelo'].with_context(context).search([('piloto_id','=',17)])
            for vuelo in vuelos:
                env['leulit.vuelo_tipo_line'].with_context(context).search([('vuelo_id','=',vuelo.id)]).unlink()
                new_cr.commit()
                env['leulit.weight_and_balance'].with_context(context).search([('vuelo_id','=',vuelo.id)]).unlink()
                new_cr.commit()
                env['leulit.performance'].with_context(context).search([('vuelo','=',vuelo.id)]).unlink()
                new_cr.commit()
                vuelo.unlink()
                new_cr.commit()
        _logger.error('################### set_unlink_vuelo fin thread')