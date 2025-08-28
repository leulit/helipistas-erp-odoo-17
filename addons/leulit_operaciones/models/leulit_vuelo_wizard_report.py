# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import timedelta

import logging
_logger = logging.getLogger(__name__)


class leulit_vuelo_wizard_report(models.TransientModel):
    _name           = "leulit.vuelo_wizard_report"
    _description    = "leulit_vuelo_wizard_report"


    helicoptero_id = fields.Many2one(comodel_name='leulit.helicoptero', string='Helicoptero')
    piloto_id = fields.Many2one(comodel_name='leulit.piloto', string='Piloto')
    piloto_uid = fields.Many2one(comodel_name='leulit.piloto', string='Piloto', domain="[('user_id','=',uid)]")
    informe = fields.Selection([("leulit_20190709_1846_report","Technical Log"),
                                ("leulit_registro_vuelosaeronave_report","Registro de Vuelos de la Aeronave"),
                                ("leulit_registro_consumosaeronave_report","Consumos por vuelo"),
                                ("leulit_registro_ciclos_report","Registro de Ciclos"),], "Informe")
    from_date = fields.Date('Desde')
    to_date = fields.Date('Hasta')

    def create_alumno_log_book_report(self):
        piloto = self.env['leulit.piloto'].search([('user_ids','in',self.env.uid)])
        if len(piloto) > 0:
            self.piloto_id = piloto.id
            return self.create_log_book_report_action()
        else:
            raise UserError(' Este usuario no esta asociado a ningún piloto. No se pueden obtener datos de sus vuelos')

    def create_report(self):
        for item in self:
            helicoptero_id = item.helicoptero_id.id
            from_date = item.from_date
            to_date = item.to_date
            informe = item.informe

            if informe == "leulit_registro_vuelosaeronave_report":
                vuelos = self.env['leulit.vuelo'].search([('helicoptero_id','=',helicoptero_id), ('fechavuelo', '>=', from_date), ('fechavuelo', '<=', to_date), ('estado', '=', 'cerrado')], limit=None, order='fechasalida asc')
                informename= 'leulit_operaciones.leulit_registro_vuelosaeronave_report'
                return self.env.ref(informename).report_action(vuelos,data=[])
            elif informe in ["leulit_registro_consumosaeronave_report"]:
                vuelos = self.env['leulit.vuelo'].search([('helicoptero_id','=',helicoptero_id), ('fechavuelo', '>=', from_date), ('fechavuelo', '<=', to_date), ('estado', '=', 'cerrado')], limit=None, order='fechasalida asc')
                informename= 'leulit_operaciones.leulit_registro_consumosaeronave_report'
                return self.env.ref(informename).report_action(vuelos,data=[])
            elif informe in ["leulit_registro_ciclos_report"]:
                vuelos = self.env['leulit.vuelo'].search([('helicoptero_id','=',helicoptero_id), ('fechavuelo', '>=', from_date), ('fechavuelo', '<=', to_date), ('estado', '=', 'cerrado')], limit=None, order='fechasalida asc')
                informename= 'leulit_operaciones.leulit_registro_ciclos_report'
                return self.env.ref(informename).report_action(vuelos,data=[])
            else:    
                delta = to_date - from_date    
                datas = []
                numdias = delta.days + 1
                for i in range(numdias):
                    fecha = (from_date + timedelta(days=i)).strftime("%Y-%m-%d")                    
                    vuelos = self.env['leulit.vuelo'].search([('helicoptero_id','=',helicoptero_id), ('fechavuelo', '>=', fecha), ('fechavuelo', '<=', fecha), ('estado', '=', 'cerrado')], limit=None, order='fechasalida asc')
                    if (len(vuelos) > 0):
                        datos1 = {
                            'firmado_por':'',     
                            'hack_estado' : False
                            }
                        data = vuelos[0].get_data_parte_vuelo_print(datos1)
                        datas.append(data)
                if len(datas) > 0:
                    informe= 'leulit_operaciones.hlp_20190709_1846_report'
                    return self.env.ref(informe).report_action([],data={'fechas': datas})
                else:
                    raise UserError("No existen vuelos para el helicoptero indicado en el rango de fechas escogido")



    def create_log_book_report_action(self):     
        for item in self:       
            tiempo_pilotomando_inicial = 0
            tiempo_instructor_act_inicial = 0
            tiempo_instructor_ato_inicio = 0
            tiempo_doblemando_inicial = 0
            tiempo_ifr_inicial = 0
            tiempo_nocturno_inicial = 0
            tiempo_total_inicial = 0
            tiempo_instructor_ato_inicial = 0
            total_pagina = 0

            primer_vuelo_piloto = self.env['leulit.vuelo'].search([
                ('estado', '=', 'cerrado'), 
                '|', '|',('piloto_id','=', item.piloto_id.id),('alumno','=', item.piloto_id.alumno.id),
                ('verificado','=', item.piloto_id.id)
            ], order='fechavuelo asc',limit=1)
            

            data = {}
            piloto_id = item.piloto_id.id
            alumno_id = item.piloto_id.alumno.id
            from_date = item.from_date
            to_date = item.to_date
            vuelos = self.env['leulit.vuelo'].search(
                [
                    ('fechavuelo', '>=', from_date), 
                    ('fechavuelo', '<=', to_date), 
                    ('estado', '=', 'cerrado'), 
                    '|', '|',('piloto_id','=', piloto_id),('alumno','=', alumno_id),('verificado','=', piloto_id)], 
                limit=None, 
                order='fechasalida asc'
            )
            
            data['piloto_id'] = piloto_id
            data['from_date'] = from_date
            data['to_date'] = to_date
            data['owner'] = item.piloto_id.name

            cursos_list = []
            for pe in self.env['leulit.parte_escuela'].search([('vuelo_id','in',vuelos.ids)]):
                cursos = []
                for curso in pe.cursos:
                    cursos.append(curso.name)
                values = {
                    'cursos': pe['cursos'],
                    'vuelo': pe['vuelo_id'],
                    'cursos_name': cursos
                }
                cursos_list.append(values)
            data['cursos_list'] = cursos_list

            vuelosarr = []
            for vuelo in vuelos:
                datos = {
                    'fechavuelo' : vuelo.fechavuelo.strftime('%d-%m-%Y'),
                    'fechasalida' : vuelo.fechasalida.strftime('%Y%m%d%H%M%S'),
                    'lugarsalida' : vuelo.lugarsalida.name,
                    'strhorasalida' : vuelo.strhorasalida,
                    'utc_strhorasalida' : vuelo.utc_horasalida,
                    'lugarllegada' : vuelo.lugarllegada.name,
                    'strhorallegada' : vuelo.strhorallegada,
                    'utc_strhorallegada' : vuelo.utc_horallegada,
                    'modelo' : vuelo.helicoptero_tipo,
                    'matricula' : vuelo.helicoptero_id.name,
                    'SE' : "X",
                    'ME' : "",
                    'strtiemposervicio' : vuelo.strtiemposervicio,
                    'tiemposervicio' : vuelo.tiemposervicio,
                    'piloto_name' : vuelo.piloto_id.name,
                    'piloto_firma' : vuelo.piloto_id.firma,
                    'landings' : vuelo.landings if vuelo.landings else 0,
                    'nightlandings' : vuelo.nightlandings if vuelo.nightlandings else 0,
                    'ifr' : vuelo.ifr,
                    'vuelo_tipo_main' : vuelo.vuelo_tipo_main,
                    'pilotoalmando' : item.piloto_id.pilotoalmando( vuelo ),
                    'copiloto' : item.piloto_id.copiloto( vuelo ),
                    'doblemando' : item.piloto_id.doblemando( vuelo ),
                    'instructor' :  True if item.piloto_id.instructor( vuelo ) and vuelo.tiempo_ato > 0.0 else False,
                    'instructoractividad' : True if item.piloto_id.instructor( vuelo ) and vuelo.tiempo_instuctor_actividad > 0.0 else False,
                    'cursos' : list( dict.fromkeys( vuelo.parte_escuela_id.cursos.ids ) ) if vuelo.parte_escuela_id and vuelo.parte_escuela_id.cursos else [],
                    'supervisor_firma' : vuelo.piloto_supervisor_id.firma,
                }
                vuelosarr.append( datos )
            vuelosarr = sorted(vuelosarr, key=lambda k: k['fechasalida'])
            vueloschunks = list( utilitylib.chunk_based_on_size( vuelosarr, 10 ) )

            ## CÁLCULO TOTALES PÁGINAS
            paginas = []
            total_paginas_previas_tiempo_vuelo = 0
            total_paginas_previas_night = 0
            total_paginas_previas_ifr = 0
            total_paginas_previas_pic = 0
            total_paginas_previas_doble_mando = 0
            total_paginas_previas_instructor_ato = 0
            total_paginas_previas_instructor_actividad = 0
            for vuelos in vueloschunks:
                total_pagina = 0
                fecha = False
                total_pagina_night = 0.0
                total_pagina_ifr = 0.0
                total_pagina_pm = 0.0
                total_pagina_dm = 0.0
                total_pagina_ins_ato = 0.0
                total_pagina_ins_act = 0.0
                
                cursosfooter = []
                for vuelo in vuelos:
                    if vuelo != None:
                        fecha = datetime.strptime( vuelo['fechavuelo'], "%d-%m-%Y")
                        total_pagina += vuelo['tiemposervicio']
                        if vuelo['nightlandings'] > 0:
                            total_pagina_night += vuelo['tiemposervicio']
                        if vuelo['ifr']:
                            total_pagina_ifr += vuelo['tiemposervicio']
                        if vuelo['pilotoalmando']:
                            total_pagina_pm += vuelo['tiemposervicio']
                        if vuelo['doblemando']:
                            total_pagina_dm += vuelo['tiemposervicio']
                        if vuelo['instructor']:
                            total_pagina_ins_ato += vuelo['tiemposervicio']
                        if vuelo['instructoractividad']:
                            total_pagina_ins_act += vuelo['tiemposervicio']
                        cursosfooter += vuelo['cursos']

                cursosfooter = list( dict.fromkeys( cursosfooter ) )
                acumulador_paginas_previas_total = 0.0
                acumulador_paginas_previas_night = 0.0
                acumulador_paginas_previas_ifr = 0.0
                acumulador_paginas_previas_dm = 0.0
                acumulador_paginas_previas_pm = 0.0
                acumulador_paginas_previas_ins_ato = 0.0
                acumulador_paginas_previas_ins_act = 0.0
                fecha = item.from_date
                if fecha:
                    acumulador_paginas_previas_total = total_paginas_previas_tiempo_vuelo if total_paginas_previas_tiempo_vuelo != 0 else item.piloto_id._calc_horas_totales_vuelo_fechas( primer_vuelo_piloto.fechavuelo, fecha )
                    acumulador_paginas_previas_night = total_paginas_previas_night if total_paginas_previas_night != 0 else item.piloto_id._calc_horas_night_fechas( primer_vuelo_piloto.fechavuelo, fecha )
                    acumulador_paginas_previas_ifr = total_paginas_previas_ifr if total_paginas_previas_ifr != 0 else item.piloto_id._calc_horas_ifr_fechas( primer_vuelo_piloto.fechavuelo, fecha )
                    acumulador_paginas_previas_pm = total_paginas_previas_pic if total_paginas_previas_pic != 0 else item.piloto_id._calc_horas_piloto_almando_fechas( primer_vuelo_piloto.fechavuelo, fecha )
                    acumulador_paginas_previas_dm = total_paginas_previas_doble_mando if total_paginas_previas_doble_mando != 0 else item.piloto_id._calc_horas_doblemando_fechas( primer_vuelo_piloto.fechavuelo, fecha )
                    acumulador_paginas_previas_ins_ato = total_paginas_previas_instructor_ato if total_paginas_previas_instructor_ato != 0 else item.piloto_id._calc_horas_instructor_ato_fechas( primer_vuelo_piloto.fechavuelo, fecha )
                    acumulador_paginas_previas_ins_act = total_paginas_previas_instructor_actividad if total_paginas_previas_instructor_actividad != 0 else item.piloto_id._calc_horas_instructor_fechas( primer_vuelo_piloto.fechavuelo, fecha )


                cursoslist = []
                for curso in self.env['leulit.curso'].search([('id','in', cursosfooter)]):
                    cursoslist.append({
                        'id' : "{0}. ".format( curso.id ),
                        'name' : curso.name,
                    })
                if len(cursoslist) > 0:
                    n = int( len(cursoslist)/ 3 )+1
                    cursoschunks = list( utilitylib.chunk_based_on_size( cursoslist, n))            
                else:
                    cursoschunks = []
                paginas.append({
                    'vuelos' : vuelos,
                    'total_pagina' : utilitylib.hlp_float_time_to_str( total_pagina ),
                    'acumulador_paginas_total' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_total + total_pagina ),
                    'acumulador_paginas_night' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_night + total_pagina_night ),
                    'acumulador_paginas_ifr' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_ifr + total_pagina_ifr ),
                    'acumulador_paginas_pm' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_pm + total_pagina_pm ),
                    'acumulador_paginas_dm' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_dm + total_pagina_dm ),
                    'acumulador_paginas_ins_ato' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_ins_ato + total_pagina_ins_ato ),
                    'acumulador_paginas_ins_act' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_ins_act + total_pagina_ins_act ),
                    'total_pagina_night' : utilitylib.hlp_float_time_to_str( total_pagina_night ),
                    'total_pagina_ifr' : utilitylib.hlp_float_time_to_str( total_pagina_ifr ),
                    'total_pagina_pm' : utilitylib.hlp_float_time_to_str( total_pagina_pm ),
                    'total_pagina_dm' : utilitylib.hlp_float_time_to_str( total_pagina_dm ),
                    'total_pagina_ins_ato' : utilitylib.hlp_float_time_to_str( total_pagina_ins_ato ),
                    'total_pagina_ins_act' : utilitylib.hlp_float_time_to_str( total_pagina_ins_act ),
                    'acumulador_paginas_previas_total' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_total ),
                    'acumulador_paginas_previas_night': utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_night ),
                    'acumulador_paginas_previas_ifr' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_ifr ),
                    'acumulador_paginas_previas_pm' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_pm ),
                    'acumulador_paginas_previas_dm' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_dm ),
                    'acumulador_paginas_previas_ins_ato' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_ins_ato ),
                    'acumulador_paginas_previas_ins_act' : utilitylib.hlp_float_time_to_str( acumulador_paginas_previas_ins_act ),
                    'cursoslist' : cursoschunks,
                })
                total_paginas_previas_tiempo_vuelo = acumulador_paginas_previas_total + total_pagina 
                total_paginas_previas_night = acumulador_paginas_previas_night + total_pagina_night 
                total_paginas_previas_ifr = acumulador_paginas_previas_ifr + total_pagina_ifr 
                total_paginas_previas_pic = acumulador_paginas_previas_pm + total_pagina_pm 
                total_paginas_previas_doble_mando = acumulador_paginas_previas_dm + total_pagina_dm 
                total_paginas_previas_instructor_ato = acumulador_paginas_previas_ins_ato + total_pagina_ins_ato 
                total_paginas_previas_instructor_actividad = acumulador_paginas_previas_ins_act + total_pagina_ins_act 
            docref = datetime.now().strftime("%Y%m%d%I%M%S")
            datos = {
                'paginas' : paginas,
                'data' : data,                
                'docref' : docref
            }            
            return self.env.ref('leulit_operaciones.leulit_report_piloto_log_book').report_action([],data=datos)



    def create_log_book_report(self):
        for item in self:
            return item.create_log_book_report_action()


