# -*- encoding: utf-8 -*-

import re
from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from lxml import etree
from datetime import datetime, timedelta
from odoo.addons.leulit import utilitylib
import odoo.netsvc as netsvc
import base64
import pytz
import math
import urllib3
from itertools import chain

from odoo.addons.leulit_operaciones import vuelo_chain_postvuelo
from odoo.addons.leulit_operaciones import vuelo_chain_cerrado

_logger = logging.getLogger(__name__)


class leulit_vuelo(models.Model):
    _name = "leulit.vuelo"
    _description = "leulit_vuelo"
    _order = "fechavuelo desc"
    _rec_name = "codigo"
    _inherit = ['mail.thread']


    PV_PILOTO = 'PILOTO'
    PV_ALUMNO = 'ALUMNO'
    PV_OPERADOR = 'OPERADOR'
    PV_VERIFICADO = 'VERIFICADO'
    PV_INSTRUCTOR = 'INSTRUCTOR'
    PV_SUPERVISOR = 'SUPERVISOR'


    def getPerfil(self, piloto):
        perfil = False
        for item in self:
            if not item.alumno and not item.verificado and not item.piloto_supervisor_id:
                if piloto.getPartnerId() == item.piloto_id.getPartnerId():
                    perfil = self.PV_PILOTO
            else:
                if item.alumno:
                    if piloto.getPartnerId() == item.alumno.getPartnerId():
                        perfil = self.PV_ALUMNO
                    if piloto.id == item.piloto_id.id:
                        perfil = self.PV_INSTRUCTOR
                    if piloto.getPartnerId() == item.alumno.getPartnerId() and piloto.id == item.piloto_id.id:
                        perfil = self.PV_PILOTO

                else:
                    if item.verificado:
                        if piloto.id == item.verificado.id:
                            perfil = self.PV_VERIFICADO
                        if piloto.id == item.piloto_id.id:
                            perfil = self.PV_INSTRUCTOR

                if item.operador:
                    if piloto.getPartnerId() == item.operador.getPartnerId():
                        perfil = self.PV_OPERADOR
                    if piloto.id == item.piloto_id.id:
                        perfil = self.PV_PILOTO

                if item.piloto_supervisor_id:
                    if piloto.id == item.piloto_supervisor_id.id:
                        perfil = self.PV_SUPERVISOR
                    if piloto.id == item.piloto_id.id:
                        perfil = self.PV_PILOTO
        return perfil


    @api.model
    def create(self, values):
        values['create_uid'] = self.env.uid
        codigo = self.env['ir.sequence'].next_by_code('leulit.vuelo')
        values.update({'codigo': codigo})
        res = super(leulit_vuelo,self).create(values)
        return res

    # Función para verificar solapamientos con otros partes de vuelo y otros partes de escuela
    def checkValidCreateWriteData(self, idvuelo, helicoptero_id, horasalida, horallegada, fechavuelo, piloto_id, estado, piloto_supervisor_id):
        if not self.isHelicopterBlocked(helicoptero_id, fechavuelo):
            objvuelo = self.env["leulit.vuelo"]
            objparteescuela = self.env["leulit.parte_escuela"]

            #verificar que no exista un vuelo para ese helicoptero posterior en estado diferente de cancelado o prevuelo
            vuelos_ids = objvuelo.search([('id','!=',idvuelo),('helicoptero_id','=',helicoptero_id),('fechavuelo','>=',fechavuelo),('horasalida','>=',horasalida),('estado','!=','cancelado'),('estado','!=','prevuelo')])
            if vuelos_ids.ids and len(vuelos_ids.ids) > 0:
                return {'error':1,'mensaje': "1 vuelo: %s" % (vuelos_ids[0].codigo)}

            #verificar que no exista un vuelo para ese helicoptero anterior en estado prevuelo
            vuelos_ids = objvuelo.search([('id','!=',idvuelo),('helicoptero_id','=',helicoptero_id),('fechavuelo','<=',fechavuelo),('horasalida','<=',horasalida),('estado','=','prevuelo')])
            if vuelos_ids.ids and len(vuelos_ids.ids) > 0:
                return {'error':1,'mensaje': "3 vuelo: %s" % (vuelos_ids[0].codigo)}

            #verificar que no exista un vuelo para ese piloto anterior en estado prevuelo
            vuelos_ids = objvuelo.search([('id','!=',idvuelo),('piloto_id','=',piloto_id),('fechavuelo','<=',fechavuelo),('horasalida','<=',horasalida),('estado','=','prevuelo')])
            if vuelos_ids.ids and len(vuelos_ids.ids) > 0:
                return {'error':1,'mensaje': "4 vuelo: %s" % (vuelos_ids[0].codigo)}

            # cojer el responsable del vuelo en caso de que fuera un vuelo de escuela.
            if piloto_supervisor_id:
                objpiloto = self.env["leulit.piloto"].search([('id','=',piloto_supervisor_id)])
            else:
                objpiloto = self.env["leulit.piloto"].search([('id','=',piloto_id)])

            #  Verificar que no exista un parte de escuela donde se solape el profesor.
            if objpiloto.profesor:
                partes_ids = objparteescuela.search([('profesor','=',objpiloto.profesor.id),('fecha','=',fechavuelo),('hora_end','>=',horasalida),('hora_start','<=',horasalida),('estado','=','cerrado')])
                if partes_ids.ids and len(partes_ids.ids) > 0:
                    return {'error':1,'mensaje': "parte: %s" % (partes_ids[0].id)}
            return {'error': 0, 'mensaje': ""}
        else:
            return {'error': 2, 'mensaje': ""}
        
    # Función para lanzar el popup que procede a cancelar el parte de vuelo.
    def wizard_pre_cancelar(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones','leulit_pre_cancelar_vuelo_popup')
        view_id = view_ref and view_ref[1] or False
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmar Cancelar Vuelo',
            'res_model': 'leulit.vuelo',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': self.id,
            'target': 'new',
        }
    
    # Función que cancela el parte de vuelo junto al parte de escuela si existe uno.
    def wizard_cancelar(self):
        self.write({ 'estado' : 'cancelado' })
        self.env['leulit.parte_escuela'].search([('vuelo_id','=',self.id)]).write({'estado': 'cancelado'})
        return True


    def initChainToCerrado(self):
        chain1 = vuelo_chain_cerrado.ComprobacionPresupuestoHandler()
        chain2 = vuelo_chain_cerrado.ComprobacionChecksHandler()
        chain3 = vuelo_chain_cerrado.ComprobacionUsuarioPilotoHandler()
        chain4 = vuelo_chain_cerrado.ComprobacionHelicopteroHandler()
        chain5 = vuelo_chain_cerrado.ComprobacionDescansoHandler()
        chain6 = vuelo_chain_cerrado.ComprobacionDatosGeneralesHandler()
        chain7 = vuelo_chain_cerrado.ComprobacionDatosCombustibleHandler()
        chain7 = vuelo_chain_cerrado.ComprobacionParteEscuelaHandler()
        chain8 = vuelo_chain_cerrado.UpdateProximoVueloHandler()

        chain1.set_next(chain2).set_next(chain3).set_next(chain4).set_next(chain5).set_next(chain6).set_next(chain7).set_next(chain8)
        return chain1


    # Función para cerrar el parte de vuelo.
    def wkf_act_cerrado(self):
        handlerVueloToCerrado = self.initChainToCerrado()
        request = vuelo_chain_cerrado.VueloChainToCerradoRequest()
        request.env = self.env
        request.vuelo_id = self.id
        request.uid = self.env.uid
        request.tipo_helicoptero = self.helicoptero_id.modelo.tipo
        handlerVueloToCerrado.handle(request)


    def get_tipo_helicoptero(self, helicoptero_id):
        if helicoptero_id:
            helicoptero = self.env['leulit.helicoptero'].browse(helicoptero_id)
            if (helicoptero):
                return helicoptero.modelo.tipo
        return ""



    def fin_act_postvuelo(self):
        for item in self:
            item.write({ 'estado' : 'postvuelo' })


    def pdf_parte_vuelo_print(self, datos):
        for item in self:
            data = item.get_data_parte_vuelo_print( datos )
            data.update({'hashcode': datos['hashcode']})
            report_name = 'leulit_operaciones.hlp_20190709_1846_report'

            pdf = self.env.ref(report_name)._render_qweb_pdf([],data={'fechas': [data]})[0]
            return base64.encodestring(pdf)

    def parte_vuelo_print(self):
        for item in self:
            datos = {
                'modelo': 'leulit.vuelo',
                'idmodelo': item.id,
                'otp': "N.A.",
                'esignature' : '',
                'fecha_firma': item.fechavuelo,
                'hack_firmado_por' : False,
                'hack_firmado_por_id' : False,        
                'hack_estado' : False
            }
            #PARTE TÉCNICO DE VUELO
            referencia ="{0}-{1}-PTV".format(item.id, item.estado)
            datos.update({'referencia': referencia})
            datos.update({'prefijo_hashcode': "PTV"})
            datos.update({'informe': "hlp_20190709_1846_report"})
            datos.update({'fecha':item.fechavuelo})
            datos.update({'helicoptero_id':item.helicoptero_id.id})            
            hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.vuelo', item.id, "PTV-{0}".format(item.codigo))
            datos.update({'hashcode': hashcode})
            datos.update({'firmado_por': None})

            data = item.get_data_parte_vuelo_print( datos )
            if self._context.get('informe') == 'leulit_technical_log_camo_report':
                #vals = {'from_date': fecha, 'to_date': fecha,'helicoptero_id': helicoptero_id}
                #tlbar = self.pool["leulit.tlb_anomalias_report"].create(vals)
                #return self.pool["leulit.tlb_anomalias_report"].create_report(tlbar)
                a = ""
            else:
                informe= 'leulit_operaciones.{0}'.format(self._context.get('informe'))
                return self.env.ref(informe).report_action([],data={'fechas': [data]})
    
    def get_data_parte_vuelo_print(self, datos1):
        firmado_por = datos1['firmado_por']
        for item in self:    
            
            numvuelospg = 6
            numanomaliaspg = 3
            numsmspg = 2        
            docref = datetime.now().strftime("%Y%m%d")		
            hashcode_interno = utilitylib.getHashOfData(docref)   
    
            data = []              
            fecha = item.fechavuelo    
            helicoptero = item.helicoptero_id
            #vuelos = self.env['leulit.vuelo'].search_read([('helicoptero_id','=',item.helicoptero_id.id),('estado','in',['postvuelo','cerrado']),('fechavuelo','=',fecha)], limit=None, order='fechasalida asc')            
            vuelos = self.env['leulit.vuelo'].search([('helicoptero_id','=',item.helicoptero_id.id),('estado','in',['postvuelo','cerrado']),('fechavuelo','=',fecha)], limit=None, order='fechasalida asc')            
            
            diaant = utilitylib.addDays(item.fechavuelo, -1)
            datoshelicoptero = self.acumulados_in_date(helicoptero, diaant)
            before_tservicio = datoshelicoptero['suma_tiemposervicio']
            before_airtime = datoshelicoptero['suma_airtime']            

            datos = self.acumulados_motor_in_date(helicoptero, diaant)
            before_nf = datos['suma_nf']
            before_ng = datos['suma_ng']

            datos = item.acumulados_motor_in_date(helicoptero, fecha)
            vuelos_nf = datos['suma_nf']
            vuelos_ng = datos['suma_ng']

            paginas = int(math.ceil(len(vuelos) / numvuelospg))
            resto = int(len(vuelos) % numvuelospg)
            filas_vacias = numvuelospg - resto

            arrpaginas = []
            totaltiemposervicio = before_tservicio
            totalairtime = before_airtime
            totaltacomng = before_ng
            totaltacomnf = before_nf
            helicoptero = ""
            arranomalias = []
            tipoaeronave = ""
            for pag in range(paginas):
                inicio = numvuelospg * pag
                fin = inicio + numvuelospg

                inianomalias = numanomaliaspg * pag
                finanomalias = inianomalias + numanomaliaspg
                arrvuelos = []
                for i in range(inicio,fin):                    
                    if i < len(vuelos):
                        totaltiemposervicio += vuelos[i].tiemposervicio
                        totalairtime += vuelos[i].airtime
                        totaltacomng += vuelos[i].ngvuelo if (vuelos[i].helicoptero_tipo == 'EC120B') else 0
                        totaltacomnf += vuelos[i]['nfvuelo'] if (vuelos[i].helicoptero_tipo == 'EC120B') else 0
                        helicoptero = vuelos[i].helicoptero_id.name
                        tipoaeronave = vuelos[i].helicoptero_tipo

                        nombre_alumno_verificado = ""
                        if vuelos[i].alumno:
                            nombre_alumno_verificado = vuelos[i].alumno.name
                        else:
                            if vuelos[i].verificado:
                                nombre_alumno_verificado = vuelos[i].verificado.name


                        tacomllegada = "{:.2f}".format( vuelos[i].tacomllegada ) if vuelos[i].tacomllegada or vuelos[i].tacomllegada == "N/A" else ''
                        strhorallegada = vuelos[i].strhorallegada
                        ngvuelo = "{:.2f}".format( vuelos[i].ngvuelo ) if vuelos[i].ngvuelo or vuelos[i].ngvuelo == "N/A" else ''
                        nfvuelo = "{:.2f}".format( vuelos[i].nfvuelo ) if vuelos[i].nfvuelo or vuelos[i].ngvuelo == "N/A" else ''
                        fuelllegada = "{:.2f}".format( vuelos[i].fuelllegada )
                        strtiemposervicio = vuelos[i].strtiemposervicio
                        strairtime = "" if vuelos[i].estado == 'postvuelo' else vuelos[i].strairtime
                        if datos1['hack_estado']:
                            tacomllegada = ""
                            strhorallegada = ""
                            ngvuelo = ""
                            nfvuelo = ""
                            fuelllegada = ""
                            strtiemposervicio = ""
                            strairtime = ""

                        arrvuelos.append( {
                            'helicoptero' : vuelos[i].helicoptero_id.name,
                            'tipo' : vuelos[i].helicoptero_tipo,
                            'codigo' : vuelos[i].codigo,
                            'fuelqty' : "{:.2f}".format( vuelos[i].fuelqty ),
                            'oilqty' : "{:.2f}".format( vuelos[i].oilqty ),
                            'vuelo_tipo_main' : vuelos[i].vuelo_tipo_main,
                            'numpae' : vuelos[i].numpae,
                            'numpax' : vuelos[i].numpax,
                            'valid_takeoff_longcg' : vuelos[i].valid_takeoff_longcg,
                            'valid_takeoff_latcg' : vuelos[i].valid_takeoff_latcg,
                            'valid_landing_longcg' : vuelos[i].valid_landing_longcg,
                            'valid_landing_latcg' : vuelos[i].valid_landing_latcg,
                            'wb_ok' : "OK" if (vuelos[i].valid_landing_latcg and vuelos[i].valid_landing_longcg and vuelos[i].valid_takeoff_latcg and vuelos[i].valid_takeoff_longcg) else "",
                            'takeoff_gw' : "{:.2f}".format( vuelos[i].weight_and_balance_id.takeoff_gw ),
                            'piloto_name' : vuelos[i].piloto_id.name,
                            'lugarsalida' : vuelos[i].lugarsalida.name,
                            'strhorasalida' : vuelos[i].strhorasalida,
                            'fuelsalida' : "{:.2f}".format( vuelos[i].fuelsalida ),
                            'strairtime' : strairtime,
                            'estado' : vuelos[i].estado,
                            'lugarllegada' : vuelos[i].lugarllegada.name,
                            'strhorallegada' : strhorallegada,
                            'strutchorasalida' : vuelos[i].utc_horasalida,
                            'strutchorallegada' : vuelos[i].utc_horallegada,
                            'tacomllegada' : tacomllegada,
                            'tacomsalida' : "{:.2f}".format( vuelos[i].tacomsalida ) if vuelos[i].tacomsalida or vuelos[i].tacomllegada == "N/A" else '',
                            'ngvuelo' : ngvuelo,
                            'nfvuelo' : nfvuelo,
                            'fuelllegada' : fuelllegada,
                            'strtiemposervicio' : strtiemposervicio,
                            # 'ordendevuelo' : "",
                            'nombre_alumno_verificado' : nombre_alumno_verificado,
                            'totaltiemposervicio' : utilitylib.hlp_float_time_to_str( totaltiemposervicio ),
                            'totalairtime' : utilitylib.hlp_float_time_to_str( totalairtime ),
                            'totaltacomng' : "{:.2f}".format( totaltacomng ),
                            'totaltacomnf' : "{:.2f}".format( totaltacomnf ),
                            'emptyline' : False,
                        })
                        anomaliasvuelo = self.env['leulit.anomalia'].search([('vuelo_id','=',vuelos[i]['id'])])            
                        for anomalia in anomaliasvuelo:                    
                            arranomalias.append({
                                'codigo' : vuelos[i].codigo,
                                'discrepancia' : anomalia.discrepancia,
                                'fecha' : anomalia.fecha,
                                'informado_por' : anomalia.informado_por.name,
                                'estado' : anomalia.estado,
                                'accion' : anomalia.accion,
                                'fecha_accion' : anomalia.fecha_accion,
                                'cas' : anomalia.cas,
                                'cerrado_por' : anomalia.cerrado_por.name
                            })
                    else:
                        arrvuelos.append({
                            'helicoptero' : "",
                            'tipo' : "",
                            'codigo' : "",
                            'fuelqty' : "",
                            'oilqty' : "",
                            'vuelo_tipo_main' : "",
                            'numpae' : "",
                            'numpax' : "",
                            'valid_takeoff_longcg' : "",
                            'valid_takeoff_latcg' : "",
                            'valid_landing_longcg' : "",
                            'valid_landing_latcg' : "",
                            'wb_ok' : "",
                            'takeoff_gw' : "",
                            'piloto_name' : "",
                            'lugarsalida' : "",
                            'strhorasalida' : "",
                            'fuelsalida' : "",
                            'strairtime' : "",
                            'estado' : "",
                            'lugarllegada' : "",
                            'strhorallegada' : "",
                            'strutchorasalida' : "",
                            'strutchorallegada' : "",
                            'tacomllegada' : "",
                            'tacomsalida' : "",
                            'ngvuelo' : "",
                            'nfvuelo' : "",
                            'fuelllegada' : "",
                            'strtiemposervicio' : "",
                            'strtiemposervicio' : "",
                            # 'ordendevuelo' : "",
                            'nombre_alumno_verificado' : "",
                            'totaltiemposervicio' : "",
                            'totalairtime' : "",
                            'totaltacomng' : "",
                            'totaltacomnf' : "",
                            'emptyline' : False,
                        })               

                numpaginasanomalias = int(len(arranomalias)/numanomaliaspg)
                resto = len(arranomalias) % numanomaliaspg
                anadir = numanomaliaspg - resto
                for j in range(0,anadir):
                    arranomalias.append({
                        'codigo' : "",
                        'discrepancia' : "",
                        'fecha' : "",
                        'informado_por' : "",
                        'estado' : "",
                        'accion' : "",
                        'fecha_accion' : "",
                        'cas' : "",
                        'cerrado_por' : ""
                    })

                arrpaginas.append({
                    'vuelos' : arrvuelos,
                    'anomalias' : arranomalias[inianomalias:finanomalias],
                    'smss' : [{},{}]
                })

            firmado_por = firmado_por if firmado_por else self.env.user.name
            company_helipistas = self.env['res.company'].search([('name','like','Helipistas')])
            data = {
                'logo_hlp' : company_helipistas.logo_reports if company_helipistas else False,
                'paginas' : arrpaginas,
                'before_tservicio': utilitylib.hlp_float_time_to_str( before_tservicio ),
                'before_airtime': utilitylib.hlp_float_time_to_str( before_airtime ),
                'before_nf': "{:.2f}".format( before_nf ),
                'before_ng': "{:.2f}".format( before_ng ),
                'vuelos_nf': "{:.2f}".format( vuelos_nf ),
                'vuelos_ng': "{:.2f}".format( vuelos_ng ),
                'docref' : docref,
                'hashcode' : False,
                'helicoptero' : helicoptero,
                'tipoaeronave' : tipoaeronave,
                'firmado_por'  : firmado_por,
                'hashcode_interno' : hashcode_interno,
                'totaltiemposervicio' : utilitylib.hlp_float_time_to_str( totaltiemposervicio ),
                'totaltacomng' : "{:.2f}".format( totaltacomng ),
                'totalairtime' : utilitylib.hlp_float_time_to_str( totalairtime ),
                'totaltacomnf' : "{:.2f}".format( totaltacomnf ),
                'fecha' : fecha.strftime('%d-%m-%Y'),
            }
            return data
        

    def pdf_vuelo_print_report(self, datos):
        for item in self:
            data = item.get_data_vuelo_print_report(datos)
            data.update({'hashcode': datos['hashcode']})
            data.update({'firmado_por': datos['firmado_por']})
            report_name = 'leulit_operaciones.ficha_vuelo_report'
            pdf = self.env.ref(report_name)._render_qweb_pdf([],data)[0]      
            return base64.encodestring(pdf)

    def imprimir_report(self,id):
        vuelo = self.search([('id','=',id)])
        vuelo.sudo().vuelo_print_report()
    
    def vuelo_print_report(self):
        try:
            for item in self:
                datos = {
                    'modelo': 'leulit.vuelo',
                    'idmodelo': item.id,
                    'otp': "N.A.",
                    'esignature' : '',
                    'fecha_firma': item.fechavuelo,
                    'hack_firmado_por' : False,
                    'hack_firmado_por_id' : False,        
                    'hack_estado' : False,
                    'referencia': '',
                    'prefijo_hashcode': "POV",
                    'informe': "leulit_ficha_vuelo_report",
                    'firmado_por': ''
                }            
                hashcode = self.env['leulit_signaturedoc'].buildSignature('leulit.vuelo', item.id, "POV-{0}".format(item.codigo))
                datos.update({'hashcode': hashcode})
                if item.fechavuelo >= datetime.strptime("2022-10-03", "%Y-%m-%d").date():
                    data = item.get_data_vuelo_print_report(datos)
                    return self.env.ref('leulit_operaciones.ficha_vuelo_report').report_action([],data=data)
                else:
                    data = item.get_data_vuelo_print_report_4_0_1(datos)
                    return self.env.ref('leulit_operaciones.ficha_vuelo_report_4_0_1').report_action([],data=data)
        except Exception as e:
            raise UserError ('Faltan datos en el parte de vuelo, revisar antes de seguir.')
    

    def get_data_vuelo_print_report(self, datos):
        for item in self:
            alternativosarr = []
            for alternativo in item.alternativos:
                alternativosarr.append(alternativo.name)
            combustiblealternativo = (item.consumomedio_vuelo if item.consumomedio_vuelo else 0.0) * (item.distancia_alternativo if item.distancia_alternativo else 0.0)
            notam_info = item.notaminfo
            # notam_info = re.sub("(?s)<div(?: [^>]*)?>","", item.notaminfo)
            # notam_info = re.sub("</div>","", notam_info)
            notam_info = re.sub("(?s)header","", item.notaminfo)
            datetime_salida_utc = self.getDateTimeUTC(item.fechavuelo, item.horasalida, item.lugarsalida.tz)
            hora_salida_utc = utilitylib.leulit_datetime_to_float_time(datetime_salida_utc)
            datetime_llegada_utc = self.getDateTimeUTC(item.fechavuelo, item.horallegadaprevista, item.lugarllegada.tz)
            hora_llegada_utc = utilitylib.leulit_datetime_to_float_time(datetime_llegada_utc)
            aerovias = []
            vuelo = {
                'fecha' : item.fechavuelo,
                'codigo' : item.codigo,
                'alumno_name' : item.alumno.name,
                'verificado_name' : item.verificado.name,
                'piloto_name' : item.piloto_id.name,
                'piloto_foto' : item.foto_piloto,
                'piloto_supervisor_name' : item.piloto_supervisor_id.name,
                'numtripulacion' : item.numtripulacion,
                'numpae' : item.numpae,
                'numpax' : item.numpax,
                'helicoptero_name' : item.helicoptero_id.name,
                'helicoptero_tipo' : item.helicoptero_tipo,
                'helicoptero_modelo' : item.helicoptero_modelo,
                'lugarsalida' : item.lugarsalida.name,
                'strhorasalida' : item.strhorasalida,
                'hora_salida_utc' : utilitylib.hlp_float_time_to_str(hora_salida_utc),
                'lugarllegada' : item.lugarllegada.name,
                'horallegadaprevista' : utilitylib.hlp_float_time_to_str(item.horallegadaprevista),
                'hora_llegada_utc' : utilitylib.hlp_float_time_to_str(hora_llegada_utc),
                'alternativos' : alternativosarr,
                'distancia_alternativo' : item.distancia_alternativo,      
                'tiempo_vuelo_max' : item.tiempo_vuelo_max,
                'strtiempoprevisto' : item.strtiempoprevisto,
                'distanciatotalprevista' : item.distanciatotalprevista,
                'velocidadprevista' : item.velocidadprevista,
                'DENSIDAD_COMBUSTIBLE' : utilitylib.DENSIDAD_COMBUSTIBLE.get(item.helicoptero_tipo if item.helicoptero_tipo else "", 0),
                'consumomedio_vuelo' : item.consumomedio_vuelo,
                'consumomedio_vuelo_kg' : item.consumomedio_vuelo_kg,
                'consumomedio_vuelo_gal' : item.consumomedio_vuelo_gal,
                'oilqty' : item.oilqty,
                'fuelqty' : item.fuelqty,
                'fuelqty_kg' : item.fuelqty_kg,
                'fuelqty_gal' : item.fuelqty_gal,
                'reservasfuel' : item.reservasfuel,
                'rodaje' : item.rodaje,
                'contingencia' : item.contingencia,
                'combustiblealternativo' : combustiblealternativo,
                'combustiblealternativo_kg' : utilitylib.convert_litros_to_kg(combustiblealternativo, item.helicoptero_tipo),
                'combustiblealternativo_gal' : utilitylib.convert_litros_to_gal(combustiblealternativo, item.helicoptero_tipo),
                'combustibletrayecto' : item.combustibletrayecto,
                'combustibletrayecto_kg' : utilitylib.convert_litros_to_kg(item.combustibletrayecto, item.helicoptero_tipo),
                'combustibletrayecto_gal' : utilitylib.convert_litros_to_gal(item.combustibletrayecto, item.helicoptero_tipo),
                'combustibleminimo' : item.combustibleminimo,
                'combustibleminimo_kg' : utilitylib.convert_litros_to_kg(item.combustibleminimo, item.helicoptero_tipo),
                'combustibleminimo_gal' : utilitylib.convert_litros_to_gal(item.combustibleminimo, item.helicoptero_tipo),
                'combustibleextra' : item.combustibleextra,
                'combustibleextra_kg' : utilitylib.convert_litros_to_kg(item.combustibleextra, item.helicoptero_tipo),
                'combustibleextra_gal' : utilitylib.convert_litros_to_gal(item.combustibleextra, item.helicoptero_tipo),
                'fuelsalida' : item.fuelsalida,
                'fuelsalida_kg' : item.fuelsalida_kg,
                'fuelsalida_gal' : item.fuelsalida_gal,
                # 'planvueloATS_notneeded' : item.planvueloATS_notneeded,
                # 'planvueloATS_notneeded_desc' : item.planvueloATS_notneeded_desc,
                'aerovia_ids' : [],
                'silabus_ids' : [],
                'wandb_isR44andEC120' : item.helicoptero_tipo not in ('R22','CABRI G2'),
                'wandb_isEC120' : item.helicoptero_tipo not in ('R22','CABRI G2','R44'),
                'wandb_isHIL' : item.helicoptero_id.name == 'EC-HIL',
                'wandb_isCABRIG2' : item.helicoptero_tipo not in ('R22','EC120B','R44'),
                'wandb_isR22andR44' : item.helicoptero_tipo not in ('CABRI G2','EC120B'),
                'wandb_isR44' : item.helicoptero_tipo not in ('R22','CABRI G2','EC120B'),
                'wandb_isR44II' : 'II' in item.helicoptero_modelo and item.helicoptero_tipo in ('R44'),
                'wandb_isR44I' : 'II' not in item.helicoptero_modelo and item.helicoptero_tipo in ('R44'),
                'color_valid_takeoff_longcg' : "#ffffff" if item.valid_takeoff_longcg else "#E9967A",
                'color_valid_takeoff_latcg' : "#ffffff" if item.valid_takeoff_latcg else "#E9967A",
                'color_valid_landing_longcg' : "#ffffff" if item.valid_landing_longcg else "#E9967A",
                'color_valid_landing_latcg' : "#ffffff" if item.valid_landing_latcg else "#E9967A",
                'indicativometeo' : item.indicativometeo,
                'meteo' : item.meteo,
                'notaminfo' : notam_info,
                'meteo_imprimir_report' : item.meteo_imprimir_report,
                'balsa' : item.balsa,
                'flotadores' : item.flotadores,
                'chalecos' : item.chalecos,
            }
            if len(item.silabus_ids) > 0:
                silabusarr = []
                for silabus in item.silabus_ids:                    
                    silabusarr.append({
                        'curso' : silabus.rel_curso.name,
                        'name' : silabus.rel_silabus.name,
                    })
                vuelo['silabus_ids'] = silabusarr
            if len(item.aerovia_ids) > 0:
                aerovias = []
                tiempo_desde_inicio = 0
                for aerovia in item.aerovia_ids:
                    tiempo_desde_inicio += aerovia.tiempoprevisto
                    aerovias.append({
                        'name' : aerovia.aerovia_id.name,
                        'distancia' : "{:.2f}".format( aerovia.distancia ),
                        'dist' : aerovia.distancia,
                        'rumbo' : "{:.2f}".format( aerovia.rumbo ),
                        'strtiempoprevisto' : aerovia.strtiempoprevisto,
                        'altitudprevista' : aerovia.altitudprevista,
                        'altitudseguridad' : aerovia.altitudseguridad,
                        'tiempo_desde_inicio' : utilitylib.leulit_float_time_to_str( tiempo_desde_inicio ),
                    })
                for item_de_20_mins in range(int(item.tiempoprevisto/0.333333333333333)):
                    if item_de_20_mins == 0:
                        aerovias.append({
                            'name' : 'Combustible a bordo',
                            'distancia' : False,
                            'dist' : False,
                            'rumbo' : False,
                            'strtiempoprevisto' : False,
                            'altitudprevista' : False,
                            'altitudseguridad' : False,
                            'tiempo_desde_inicio' : '00:00',
                        })
                        name = "20 minutos de vuelo"
                        time = "00:20"
                    if item_de_20_mins == 1:
                        name = "40 minutos de vuelo"
                        time = "00:40"
                    if item_de_20_mins == 2:
                        name = "60 minutos de vuelo"
                        time = "01:00"
                    if item_de_20_mins == 3:
                        name = "80 minutos de vuelo"
                        time = "01:20"
                    if item_de_20_mins == 4:
                        name = "100 minutos de vuelo"
                        time = "01:40"
                    if item_de_20_mins == 5:
                        name = "120 minutos de vuelo"
                        time = "02:00"
                    if item_de_20_mins == 6:
                        name = "140 minutos de vuelo"
                        time = "02:20"
                    if item_de_20_mins == 7:
                        name = "160 minutos de vuelo"
                        time = "02:40"
                    if item_de_20_mins == 8:
                        name = "180 minutos de vuelo"
                        time = "03:00"
                    if item_de_20_mins == 9:
                        name = "200 minutos de vuelo"
                        time = "03:20"
                    aerovias.append({
                        'name' : name,
                        'distancia' : False,
                        'dist' : False,
                        'rumbo' : False,
                        'strtiempoprevisto' : False,
                        'altitudprevista' : False,
                        'altitudseguridad' : False,
                        'tiempo_desde_inicio' : time,
                    })

                aerovias.sort(key=lambda x: x['tiempo_desde_inicio'])
                distancia_desde_inicio = 0
                sequence = 1
                for aerovia in aerovias:
                    minutos = utilitylib.leulit_float_time_to_minutes(utilitylib.leulit_str_to_float_time(aerovia['tiempo_desde_inicio']))
                    combus_minimo = item.consumomedio_vuelo * minutos
                    combus_plan = item.fuelsalida - combus_minimo
                    distancia_desde_inicio += aerovia['dist']
                    aerovia['distancia_desde_inicio'] = "" if not aerovia['distancia'] else "{:.2f}".format( distancia_desde_inicio ),
                    aerovia['distancia_desde_inicio'] = aerovia['distancia_desde_inicio'][0]
                    aerovia['combus_l'] = "{0}".format(round(combus_plan, 2))
                    aerovia['combus_k'] = "{0}".format(utilitylib.convert_litros_to_kg( combus_plan, item.helicoptero_tipo ))
                    aerovia['combus_g'] = "{0}".format(utilitylib.convert_litros_to_gal(combus_plan, item.helicoptero_tipo))
                    aerovia['sequence'] = sequence
                    sequence += 1
                    
                vuelo['aerovia_ids'] = aerovias
                vuelo['comentario_ruta'] = item.ruta_id.comentarios

            data = {'ids': item.ids}

            arrawandb  = utilitylib.getPropertiesArray(item.weight_and_balance_id)
            arrawandb.update({'masa_mop': arrawandb['frs'] + arrawandb['emptyweight']})
            arrawandb.update({'masa_mop_long_moment': round(arrawandb['frs_long_moment'] + arrawandb['emptyweight_long_moment'],2)})
            arrawandb.update({'masa_mob_lat_moment': round(arrawandb['frs_lat_moment'] + arrawandb['emptyweight_lat_moment'],2)})
            arrawandb.update({'masa_mob_lat_moment': round(arrawandb['frs_lat_moment'] + arrawandb['emptyweight_lat_moment'],2)})
            arrawandb.update({'masa_mop_long_moment2': round(arrawandb['masa_mop_long_moment'] / arrawandb['masa_mop'],2) if arrawandb['masa_mop'] > 0 else 0.0})
            arrawandb.update({'masa_mob_lat_moment2': round(arrawandb['masa_mob_lat_moment'] / arrawandb['masa_mop'],2) if arrawandb['masa_mop'] > 0 else 0.0})

            docref = datetime.now().strftime("%Y%m%d")
            hashcode_interno = utilitylib.getHashOfData(docref)
            company_helipistas = self.env['res.company'].search([('name','like','Helipistas')])
            data = {
                'logo_hlp' : company_helipistas.logo_reports if company_helipistas else False,
                'vuelos' : [vuelo],
                'wandb' : arrawandb,
                'hashcode_interno' : hashcode_interno,
                'performance_ige': item.performance.ige,
                'performance_oge': item.performance.oge,
                'performance_h_v' : item.helicoptero_id.modelo.performance_altura_velocidad if item.helicoptero_id.modelo.performance_altura_velocidad else False
            }
            return data

    def get_data_vuelo_print_report_4_0_1(self, datos):
        for item in self:
            alternativosarr = []
            for alternativo in item.alternativos:
                alternativosarr.append(alternativo.name)
            combustiblealternativo = (item.consumomedio_vuelo if item.consumomedio_vuelo else 0.0) * (item.distancia_alternativo if item.distancia_alternativo else 0.0)

            aerovias = []
            vuelo = {
                'fecha' : item.fechavuelo,
                'codigo' : item.codigo,
                'alumno_name' : item.alumno.name,
                'verificado_name' : item.verificado.name,
                'piloto_name' : item.piloto_id.name,
                'piloto_supervisor_name' : item.piloto_supervisor_id.name,
                'numtripulacion' : item.numtripulacion,
                'numpae' : item.numpae,
                'numpax' : item.numpax,
                'helicoptero_name' : item.helicoptero_id.name,
                'helicoptero_tipo' : item.helicoptero_tipo,
                'helicoptero_modelo' : item.helicoptero_modelo,
                'lugarsalida' : item.lugarsalida.name,
                'strhorasalida' : item.strhorasalida,
                'lugarllegada' : item.lugarllegada.name,
                'horallegadaprevista' : utilitylib.hlp_float_time_to_str(item.horallegadaprevista),
                'alternativos' : alternativosarr,
                'distancia_alternativo' : item.distancia_alternativo,      
                'tiempo_vuelo_max' : item.tiempo_vuelo_max,
                'strtiempoprevisto' : item.strtiempoprevisto,
                'distanciatotalprevista' : item.distanciatotalprevista,
                'velocidadprevista' : item.velocidadprevista,
                'DENSIDAD_COMBUSTIBLE' : utilitylib.DENSIDAD_COMBUSTIBLE.get(item.helicoptero_tipo if item.helicoptero_tipo else "", 0),
                'consumomedio_vuelo' : item.consumomedio_vuelo,
                'consumomedio_vuelo_kg' : item.consumomedio_vuelo_kg,
                'consumomedio_vuelo_gal' : item.consumomedio_vuelo_gal,
                'oilqty' : item.oilqty,
                'fuelqty' : item.fuelqty,
                'fuelqty_kg' : item.fuelqty_kg,
                'fuelqty_gal' : item.fuelqty_gal,
                'reservasfuel' : item.reservasfuel,
                'rodaje' : item.rodaje,
                'contingencia' : item.contingencia,
                'combustiblealternativo' : combustiblealternativo,
                'combustiblealternativo_kg' : utilitylib.convert_litros_to_kg(combustiblealternativo, item.helicoptero_tipo),
                'combustiblealternativo_gal' : utilitylib.convert_litros_to_gal(combustiblealternativo, item.helicoptero_tipo),
                'combustibletrayecto' : item.combustibletrayecto,
                'combustibletrayecto_kg' : utilitylib.convert_litros_to_kg(item.combustibletrayecto, item.helicoptero_tipo),
                'combustibletrayecto_gal' : utilitylib.convert_litros_to_gal(item.combustibletrayecto, item.helicoptero_tipo),
                'combustibleminimo' : item.combustibleminimo,
                'combustibleminimo_kg' : utilitylib.convert_litros_to_kg(item.combustibleminimo, item.helicoptero_tipo),
                'combustibleminimo_gal' : utilitylib.convert_litros_to_gal(item.combustibleminimo, item.helicoptero_tipo),
                'combustibleextra' : item.combustibleextra,
                'combustibleextra_kg' : utilitylib.convert_litros_to_kg(item.combustibleextra, item.helicoptero_tipo),
                'combustibleextra_gal' : utilitylib.convert_litros_to_gal(item.combustibleextra, item.helicoptero_tipo),
                'fuelsalida' : item.fuelsalida,
                'fuelsalida_kg' : item.fuelsalida_kg,
                'fuelsalida_gal' : item.fuelsalida_gal,
                # 'planvueloATS_notneeded' : item.planvueloATS_notneeded,
                # 'planvueloATS_notneeded_desc' : item.planvueloATS_notneeded_desc,
                'aerovia_ids' : [],
                'silabus_ids' : [],
                'wandb_isR44andEC120' : item.helicoptero_tipo not in ('R22','CABRI G2'),
                'wandb_isEC120' : item.helicoptero_tipo not in ('R22','CABRI G2','R44'),
                'wandb_isHIL' : item.helicoptero_id.name == 'EC-HIL',
                'wandb_isCABRIG2' : item.helicoptero_tipo not in ('R22','EC120B','R44'),
                'wandb_isR22andR44' : item.helicoptero_tipo not in ('CABRI G2','EC120B'),
                'wandb_isR44' : item.helicoptero_tipo not in ('R22','CABRI G2','EC120B'),
                'color_valid_takeoff_longcg' : "#ffffff" if item.valid_takeoff_longcg else "#E9967A",
                'color_valid_takeoff_latcg' : "#ffffff" if item.valid_takeoff_latcg else "#E9967A",
                'color_valid_landing_longcg' : "#ffffff" if item.valid_landing_longcg else "#E9967A",
                'color_valid_landing_latcg' : "#ffffff" if item.valid_landing_latcg else "#E9967A",
                'indicativometeo' : item.indicativometeo,
                'meteo' : item.meteo,
                'notaminfo' : item.notaminfo,
                'meteo_imprimir_report' : item.meteo_imprimir_report,
            }
            if len(item.silabus_ids) > 0:
                silabusarr = []
                for silabus in item.silabus_ids:                    
                    silabusarr.append({
                        'curso' : silabus.rel_curso.name,
                        'name' : silabus.rel_silabus.name,
                    })
                vuelo['silabus_ids'] = silabusarr
            if len(item.aerovia_ids) > 0:
                aerovias = []
                for aereovia in item.aerovia_ids:
                    aerovias.append({
                        'name' : aereovia.aerovia_id.name,
                        'distancia' : "{:.2f}".format( aereovia.distancia ),
                        'rumbo' : "{:.2f}".format( aereovia.rumbo ),
                        'strtiempoprevisto' : aereovia.strtiempoprevisto,
                        'altitudprevista' : aereovia.altitudprevista,
                        'altitudseguridad' : aereovia.altitudseguridad,
                    })
                vuelo['aerovia_ids'] = aerovias
                vuelo['comentario_ruta'] = item.ruta_id.comentarios

            data = {'ids': item.ids}

            arrawandb  = utilitylib.getPropertiesArray(item.weight_and_balance_id)
            arrawandb.update({'masa_mop': arrawandb['frs'] + arrawandb['emptyweight']})
            arrawandb.update({'masa_mop_long_moment': round(arrawandb['frs_long_moment'] + arrawandb['emptyweight_long_moment'],2)})
            arrawandb.update({'masa_mob_lat_moment': round(arrawandb['frs_lat_moment'] + arrawandb['emptyweight_lat_moment'],2)})
            arrawandb.update({'masa_mob_lat_moment': round(arrawandb['frs_lat_moment'] + arrawandb['emptyweight_lat_moment'],2)})
            arrawandb.update({'masa_mop_long_moment2': round(arrawandb['masa_mop_long_moment'] / arrawandb['masa_mop'],2) if arrawandb['masa_mop'] > 0 else 0.0})
            arrawandb.update({'masa_mob_lat_moment2': round(arrawandb['masa_mob_lat_moment'] / arrawandb['masa_mop'],2) if arrawandb['masa_mop'] > 0 else 0.0})

            docref = datetime.now().strftime("%Y%m%d")
            hashcode_interno = utilitylib.getHashOfData(docref)   
            data = {
                'vuelos' : [vuelo],
                'wandb' : arrawandb,
                'hashcode_interno' : hashcode_interno,
                'performance_ige':  item.performance.ige,
                'performance_oge':  item.performance.oge,
            }
            return data

    
    def checkDescansoPiloto(self, idvuelo, horasalida, fechavuelo, piloto_id, tPrevisto):
        sw = False
        swPrimerVuelo = True
        hPrimerVuelo = 0.0
        totalTiempoVuelo = round(tPrevisto, 2)
        hSalida = horasalida
        vueloIds = self.search([('id','!=',idvuelo),('estado','=','cerrado'),('fechavuelo','=',fechavuelo),('piloto_id','=',piloto_id),('horasalida','<',horasalida)], order="horasalida desc")
        if vueloIds:
            for vuelo in vueloIds:
                if (round(vuelo.horallegada + 0.05, 2) >= round(hSalida, 2)) and swPrimerVuelo == True:
                    hSalida = vuelo.horasalida
                    totalTiempoVuelo = totalTiempoVuelo + vuelo.tiemposervicio
                    sw = True
                else:
                    if sw == True:
                        if totalTiempoVuelo > 3:
                            return True
                        else:
                            return False
                    else:
                        if (round(vuelo.horallegada + 0.05, 2) >= round(hSalida, 2)):
                            hSalida = vuelo.horasalida
                            totalTiempoVuelo = totalTiempoVuelo + vuelo.tiemposervicio
                        else:
                            if swPrimerVuelo == True:
                                hSalida = vuelo.horasalida
                                totalTiempoVuelo = vuelo.tiemposervicio
                                swPrimerVuelo = False
                                hPrimerVuelo = round(vuelo.horallegada, 2)
                            else:
                                descanso = round(totalTiempoVuelo * 20 / 60, 2)
                                if ((round(hPrimerVuelo + descanso, 2)) >= round(horasalida, 2)):
                                    return True
                                else:
                                    return False
        return False

    
    def initChainToPostvuelo(self):
        chain1 = vuelo_chain_postvuelo.ComprobacionTripulacionEnVuelosPostvueloHandler()
        chain2 = vuelo_chain_postvuelo.ComprobacionChecksHandler()
        chain3 = vuelo_chain_postvuelo.ComprobacionTripulantesTipoActividadHandler()
        chain4 = vuelo_chain_postvuelo.ComprobacionUsuarioPilotoHandler()
        chain5 = vuelo_chain_postvuelo.ComprobacionHelicopteroHandler()
        chain6 = vuelo_chain_postvuelo.ComprobacionOverlapPartesEscuelaVueloHandler()
        chain7 = vuelo_chain_postvuelo.ComprobacionParteEscuelaHandler()
        chain8 = vuelo_chain_postvuelo.ComprobacionDatosGeneralesHandler()
        chain9 = vuelo_chain_postvuelo.ComprobacionDatosCombustibleHandler()
        chain10 = vuelo_chain_postvuelo.ComprobacionPerfilesFormacionHandler()

        chain1.set_next(chain2).set_next(chain3).set_next(chain4).set_next(chain5).set_next(chain6).set_next(chain7).set_next(chain8).set_next(chain9).set_next(chain10)
        return chain1


    def wkf_act_postvuelo(self):
        handlerVueloToPostvuelo = self.initChainToPostvuelo()
        request = vuelo_chain_postvuelo.VueloChainToPostvueloRequest()
        request.env = self.env
        request.vuelo_id = self.id
        request.uid = self.env.uid
        request.tipo_helicoptero = self.helicoptero_id.modelo.tipo
        handlerVueloToPostvuelo.handle(request)


    def hasFlightHours(self, horas, helicoptero_id):
        return helicoptero_id.horas_remanente > horas


    def isHelicopterEnTaller(self, helicoptero_id):
        res = False
        if helicoptero_id.statemachine == 'En taller':
            res = True
        return res


    def check_exists_prev_flight_open(self, helicoptero, fecha, codigo):
        if not fecha:
            self._calc_fecha_salida()
            fecha = self.fechasalida
        if helicoptero:
            sql = """
                    SELECT
                        vuelo.codigo
                    FROM
                        leulit_vuelo as vuelo
                    WHERE
                        vuelo.estado in ('prevuelo','postvuelo')
                        AND vuelo.helicoptero_id = '{0}'
                        AND vuelo.fechasalida <= '{1}'
                        AND vuelo.codigo <> '{2}'
                    ORDER BY vuelo.fechasalida ASC
                    LIMIT 1
            """.format(helicoptero,fecha,codigo)
            self._cr.execute(sql)
            valor = False
            if self._cr.rowcount > 0:
                valor = list(self._cr.fetchall()[0])[0]
            return valor
        return False

    
    def check_exists_flight_closed(self, helicoptero, fecha):
        sql = """
                SELECT 
                    vuelo.codigo
                FROM 
                    leulit_vuelo as vuelo
                WHERE 
                    vuelo.estado = 'cerrado'
                    AND vuelo.helicoptero_id = '%s' 
                    AND vuelo.fechasalida >= '%s'   
                ORDER BY vuelo.fechasalida ASC
                LIMIT 1                 
                """
        sql = sql % (helicoptero, fecha)
        self._cr.execute(sql)
        valor = False
        if self._cr.rowcount > 0:
            valor = list(self._cr.fetchall()[0])[0]
        return valor


    def user_okey_close_postvuelo(self, piloto, supervisor):
        sw = False
        if piloto:
            if piloto.partner_id.user_ids:
                sw = piloto.partner_id.user_ids.id == self.env.uid
        if sw == False and supervisor:
            if supervisor.partner_id.user_ids:
                sw = supervisor.partner_id.user_ids.id == self.env.uid
        return sw


    def vuelo_print(self):                
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones', 'leulit_vuelos_form_popup_ficha')
        view_id = view_ref and view_ref[1] or False
        #self._context.update({'default_meteo_imprimir_report':True})
        return {
             'type': 'ir.actions.act_window',
             'name': 'Pop up Ficha Parte de Vuelo',
             'res_model': 'leulit.vuelo',
             'view_mode': 'form',
             'view_id': view_id,
             'res_id': self.id,
             'target': 'new',
             'context': self._context,
        }

    
    def wizard_add_wb(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones', 'leulit_20210128_1642_form')
        view_id = view_ref and view_ref[1] or False
        for item in self:
            wandb = self.env['leulit.weight_and_balance'].search([('vuelo_id','=',item.id)])
            fls = 0.0
            frs = item.peso_piloto
            if item.operador:
                fls = item.operador.peso_piloto
            if item.alumno and item.piloto_id:
                frs = item.alumno.peso_piloto
                if item.alumno.partner_id.id != item.piloto_id.partner_id.id:
                    fls = item.peso_piloto
                else:
                    fls = 0.0
            if item.verificado:
                frs = item.verificado.peso_piloto
                fls = item.peso_piloto
            
            cyclic_cb = False
            pedals_cb = False
            collective_cb = False
            dualcontrols_cb = False
            # Cyclic Colective y Pedals en estado remove cuando hay Pic o Pic operador  Vista Nueva (Parte vuelo views branch)
            if not item.alumno and not item.verificado:
                if item.helicoptero_tipo == 'R22':
                    cyclic_cb = True
                    pedals_cb = True
                    collective_cb = True
                if item.helicoptero_tipo in ['R44','EC120B']:
                    dualcontrols_cb = True
            
            context = {
                'default_vuelo_id'              : item.id,
                'default_helicoptero_id'        : item.helicoptero_id.id,
                'default_helicoptero_tipo'      : item.helicoptero_tipo,
                'default_helicoptero_modelo'    : item.helicoptero_id.modelo.name,
                'default_fueltakeoff'           : item.fuelsalida_kg,
                'default_fuellanding'           : item.combustiblelanding_kg,
                'default_frs'                   : frs,
                'default_fls'                   : fls,
                'default_cyclic_cb'             : cyclic_cb,
                'default_pedals_cb'             : pedals_cb,
                'default_collective_cb'         : collective_cb,
                'default_dualcontrols_cb'       : dualcontrols_cb,
            }

            if wandb:
                if item.estado == 'prevuelo' or item.estado == 'postvuelo':
                    if item.helicoptero_tipo != wandb.helicoptero_tipo or item.fuelsalida_kg != wandb.fueltakeoff or item.combustiblelanding_kg != wandb.fuellanding:
                        self.env.context = context
                        wandb.change_data_vuelo()
                        wandb.updateTotals()

            if not wandb.helicoptero_tipo:
                wandb.helicoptero_tipo = item.helicoptero_tipo
            if not wandb.helicoptero_modelo:
                wandb.helicoptero_modelo = item.helicoptero_id.modelo.name
            
                
        return {
           'type'           : 'ir.actions.act_window',
           'name'           : 'Weight And Balance',
           'res_model'      : 'leulit.weight_and_balance',
           'res_id'         : wandb.id,
           'view_mode'      : 'form',
           'view_id'        : view_id,
           'target'         : 'new',
           'context'        : context,
           'nodestroy'      : True,
        }

    def obtener_peso(self):
        for item in self:
            sql = "select takeoff_gw from leulit_weight_and_balance where vuelo_id = {0} order by write_date desc".format(item.id)
            self._cr.execute(sql)
            row = list(self._cr.fetchall())
        if row:
            return row[0][0]
        else:
            return 0

    def button_performance_vuelo(self):
        peso = self.obtener_peso()
        for item in self:
            if item.helicoptero_modelo == 'EC120B':
                vista = 'leulit_performance_EC120B_form'
                if item.helicoptero_id.name == 'EC-HIL':
                    if item.weight_and_balance_id:
                        if item.weight_and_balance_id.gancho_carga_cb:
                            vista = 'leulit_performance_ECHIL_form'
            elif item.helicoptero_modelo == 'R22 Beta':
                vista = 'leulit_performance_R22_form'
            elif item.helicoptero_modelo == 'R22 Beta II':
                vista = 'leulit_performance_R22_2_form'
            elif item.helicoptero_modelo == 'R44 Astro':
                vista = 'leulit_performance_R44_form'
            elif item.helicoptero_modelo == 'R44 Raven I':
                vista = 'leulit_performance_R44_form'
            elif item.helicoptero_modelo == 'R44 Clipper I':
                vista = 'leulit_performance_R44_form'
            elif item.helicoptero_modelo == 'R44 Raven II':
                vista = 'leulit_performance_R44_2_form'
            elif item.helicoptero_modelo == 'R44 Clipper II':
                vista = 'leulit_performance_R44_2_form'
            elif item.helicoptero_modelo == 'CABRI G2':
                vista = 'leulit_performance_CABRI_G2_form'
            else:
                raise UserError ('NO SE PUEDE CALCULAR PERFORMANCE PARA ESTE MODELO PORQUE NO HA SIDO IMPLEMENTADO EN EL SISTEMA')

            view_ref = self.env['ir.model.data'].get_object_reference('leulit_operaciones', vista)
            view_id = view_ref and view_ref[1] or False

            performance = None
            # _logger.error('########### %r',item.performance)
            if item.performance:
                item.performance.write({'peso':peso,'ige':None,'oge':None})
            else:
                self.env['leulit.performance'].create({'peso':peso,'vuelo':item.id,'temperatura':0})

            # _logger.error("--obtener_peso--> peso = %r", peso)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Calcular Performance',
                'res_model': 'leulit.performance',
                'view_mode': 'form',
                'view_id': view_id,
                'res_id': item.performance.id,
                'target': 'new',
            }
        return False

    @api.depends('helicoptero_id')
    def _get_modelo_helicoptero(self):
        for item in self:
            item.helicoptero_modelo = item.helicoptero_id.modelo.name
    

    def acumulados_in_date(self, helicoptero, fecha):
        if helicoptero and helicoptero.id:
            fecha_now = "{0} 23:59:59".format(fecha)
            result = self.acumulados_between_date_and_datetime(helicoptero.id, '2000-01-01', fecha_now)
            result['airtime'] = result['suma_airtime']
            result['suma_airtime'] = result['suma_airtime'] + helicoptero.airtimestart
            result['ng'] = result['suma_ng']
            result['suma_ng'] = result['suma_ng'] + helicoptero.ngstart
            result['nf'] = result['suma_nf']
            result['suma_nf'] = result['suma_nf'] + helicoptero.nfstart
            result['suma_tiemposervicio'] = result['suma_tiemposervicio'] + helicoptero.airtimestart
        else:
            result = False
        return result


    def get_vuelos_helicoptero_range_fechas(self, helicoptero_id, from_date, to_date):
        return self.search([('estado','=','cerrado'),('helicoptero_id','=',helicoptero_id),('fechavuelo','>=',from_date),('fechavuelo','<=',to_date)], limit=None, order='fechasalida asc')



    def acumulados_motor_in_date(self, helicoptero, fecha):
        result = self.acumulados_between_date_and_datetime(helicoptero.id, helicoptero.fecha_instala_motor, "{0} 23:59:59".format(fecha))
        if result:
            result['airtime'] = result['suma_airtime']
            result['suma_airtime'] = result['suma_airtime'] + helicoptero.motor_tsn_inicio
            result['ng'] = result['suma_ng']
            result['suma_ng'] = result['suma_ng'] + helicoptero.ngstart
            result['nf'] = result['suma_nf']
            result['suma_nf'] = result['suma_nf'] + helicoptero.nfstart
            result['suma_tiemposervicio'] = result['suma_tiemposervicio'] + helicoptero.motor_tsn_inicio

        return result


    def acumulados_between_date_and_datetime(self, helicoptero, fechainicio, fechatimefin):
        sql = """
                    SELECT 
                        COALESCE(SUM(vuelo.airtime),0) as suma_airtime,
                        COALESCE(SUM(vuelo.ngvuelo),0) as suma_ng,
                        COALESCE(SUM(vuelo.nfvuelo),0) as suma_nf,
                        COALESCE(SUM(vuelo.tiemposervicio),0) as suma_tiemposervicio
                    FROM 
                        leulit_vuelo as vuelo
                    WHERE 
                        vuelo.estado = 'cerrado' 
                        AND vuelo.fechasalida <= '{0}'::timestamp
                        AND vuelo.fechavuelo::DATE >= '{1}'::DATE
                        AND vuelo.helicoptero_id = {2}
                    """.format(fechatimefin,fechainicio,helicoptero)
        result = False
        if helicoptero and fechainicio and fechatimefin:
            rows = utilitylib.runQuery(self._cr, sql)
            if len(rows) > 0:
                result = rows[0]
        else:
            result = {
                "suma_airtime": 0,
                "suma_ng" : 0,
                "suma_nf" : 0,
                "suma_tiemposervicio" : 0,
            }
        return result

    @api.depends('fechavuelo','horasalida')
    def _calc_fecha_salida(self):
        for item in self:
            date2 = utilitylib.leulit_float_time_to_str( item.horasalida )
            date1 = item.fechavuelo.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            valor = datetime.strptime(tira,"%Y-%m-%d %H:%M")
            item.fechasalida = valor

            date1 = item.fechavuelo.strftime("%d/%m/%Y")
            tira =  date1+" "+date2
            item.strfechasalida = tira


    @api.depends('fechavuelo','horallegada')
    def _calc_fecha_llegada(self):
        for item in self:
            date2 = utilitylib.leulit_float_time_to_str( item.horallegada )
            date1 = item.fechavuelo.strftime("%Y-%m-%d")
            try:
                tira =  date1+" "+date2
                valor = datetime.strptime(tira,"%Y-%m-%d %H:%M")
                item.fechallegada = valor
            except ValueError:
                item.fechallegada = False

            date1 = item.fechavuelo.strftime("%d/%m/%Y")
            tira =  date1+" "+date2
            item.strfechallegada = tira
    
    
    def _get_user_vuelo_ids(self):
        for item in self:
            item.user_vuelo_ids = False
            pilotos = self.env['leulit.piloto'].search([('user_ids','=',self.env.uid)])
            operadores = self.env['leulit.operador'].search([('user_ids','=',self.env.uid)])
            alumnos = self.env['leulit.alumno'].search([('user_ids','=',self.env.uid)])
            strpilotosids = '0'
            stroperadoresids = '0'
            stralumnosids = '0'
            if pilotos and len (pilotos) > 0:
                strpilotosids = ''
                strpilotosids = ','.join(str(i.id) for i in pilotos)
            if operadores and len (operadores) > 0:
                stroperadoresids = ''
                stroperadoresids = ','.join(str(i.id) for i in operadores)
            if alumnos and len (alumnos) > 0:
                stralumnosids = ''
                stralumnosids = ','.join(str(i.id) for i in alumnos)
            sql = """
                SELECT id FROM leulit_vuelo WHERE 
                piloto_id IN ({0})
                OR
                operador IN ({1})
                OR
                alumno IN ({2})
                OR
                verificado IN ({0})
                OR
                piloto_supervisor_id IN ({0})
            """.format(strpilotosids, stroperadoresids, stralumnosids)
            self._cr.execute(sql)
            rows = self._cr.fetchall()
            for row in rows:
                if row['id'] in item.ids:
                    item.user_vuelo_ids = True


    def _search_user_vuelo_ids(self, operator, value):
        pilotos = self.env['leulit.piloto'].search([('user_ids','=',self.env.uid)])
        operadores = self.env['leulit.operador'].search([('user_ids','=',self.env.uid)])
        alumnos = self.env['leulit.alumno'].search([('user_ids','=',self.env.uid)])
        strpilotosids = '0'
        stroperadoresids = '0'
        stralumnosids = '0'
        if pilotos and len (pilotos) > 0:
            strpilotosids = ''
            strpilotosids = ','.join(str(i.id) for i in pilotos)
        if operadores and len (operadores) > 0:
            stroperadoresids = ''
            stroperadoresids = ','.join(str(i.id) for i in operadores)
        if alumnos and len (alumnos) > 0:
            stralumnosids = ''
            stralumnosids = ','.join(str(i.id) for i in alumnos)
        sql = """
            SELECT id FROM leulit_vuelo WHERE 
            piloto_id IN ({0})
            OR
            operador IN ({1})
            OR
            alumno IN ({2})
            OR
            verificado IN ({0})
            OR
            piloto_supervisor_id IN ({0})
        """.format(strpilotosids,stroperadoresids,stralumnosids)
        self._cr.execute(sql)
        rows = self._cr.fetchall()
        ids = []
        for row in rows:
            ids.append( row[0] )
        return [('id', 'in', ids)]


    def _calc_combustible_trayecto(self, tiempoprevisto, consumomedio_vuelo):
        tiempo = tiempoprevisto
        minutosprevistos = utilitylib.leulit_float_time_to_minutes(tiempo)
        combustibleminimo = consumomedio_vuelo * (minutosprevistos)
        return round(combustibleminimo,2)

    
    @api.depends('tiempoprevisto','consumomedio_vuelo','helicoptero_tipo')
    def _get_combustibletrayecto(self):
        for item in self:
            combustibleminimo = self._calc_combustible_trayecto(item.tiempoprevisto, item.consumomedio_vuelo)
            item.combustibletrayecto = combustibleminimo
            item.combustibletrayecto_kg = utilitylib.convert_litros_to_kg( combustibleminimo, item.helicoptero_tipo )
            item.combustibletrayecto_gal = utilitylib.convert_litros_to_gal(combustibleminimo, item.helicoptero_tipo)


    @api.depends('fechasalida','helicoptero_id')
    def _get_combustible_remanente(self):
        for item in self:
            fuelremanente = 0
            if item.fechasalida:
                sql = "SELECT fuelllegada FROM leulit_vuelo WHERE estado = 'cerrado' AND fechasalida < '{0}' AND helicoptero_id = {1} ORDER BY fechasalida DESC LIMIT 1".format(item.fechasalida, item.helicoptero_id.id if item.helicoptero_id else 0)
                self._cr.execute(sql)
                if self._cr.rowcount > 0:
                    items = self._cr.fetchall()
                    fuelremanente = list(items[0])[0]
                else:
                    fuelremanente = 0
            else:
                fuelremanente = 0
            item.write({'editfuelrem':fuelremanente})
            item.fuelremanente = fuelremanente
            


    @api.depends('fechasalida','helicoptero_id')
    def _calc_delta_horas(self):
        for item in self:
            horas = 0
            if item.fechasalida:
                fecha_salida = item.fechasalida.strftime("%m/%d/%Y")
                sql = """
                    SELECT 
                        COALESCE(SUM(vuelo.airtime),0) +  leulit_helicoptero."airtimestart" as suma
                    FROM 
                        leulit_vuelo as vuelo
                        INNER JOIN leulit_helicoptero ON vuelo.helicoptero_id = leulit_helicoptero."id"
                    WHERE 
                        vuelo.estado = 'cerrado' 
                        AND vuelo.fechasalida <= '{0}' 
                        AND vuelo.helicoptero_id = {1}
                    GROUP BY
                        leulit_helicoptero."airtimestart"
                    """.format(fecha_salida, item.helicoptero_id.id if item.helicoptero_id else 0)
                self._cr.execute(sql)
                if self._cr.rowcount > 0:
                    horas = list(self._cr.fetchall()[0])[0]
            item.deltahoras = horas


    @api.depends('nightlandings','tiemposervicio')
    def _get_night_hours_vuelo(self):
        tiempo = 0.0
        for item in self:
            if item.nightlandings > 0:
                tiempo = item.tiemposervicio
            item.night_hours = tiempo


    @api.depends('vuelo_tipo_line')
    def _get_vuelo_tipo_main(self):
        for item in self:
            valor = ""
            if item.vuelo_tipo_line:
                for line in item.vuelo_tipo_line:
                    if ( not line.privado ) and line.vuelo_tipo_id:
                        valor = valor + " " + line.vuelo_tipo_id.name
            item.vuelo_tipo_main = valor

    
    def _search_vuelo_tipo_main(self, operator, value):
        idsitems = []
        if operator not in ['=','in']:
            vuelo_tipo = self.env['leulit.vuelostipo'].search([('name',operator,value)])
            for item in self.search([]):
                if item.vuelo_tipo_line:
                    for line in item.vuelo_tipo_line:
                        for tipo in vuelo_tipo:
                            if line.vuelo_tipo_id.id == tipo.id:
                                idsitems.append(item.id)
                            
        return [('id','in',idsitems)]


    def _isroldireccion(self):
        for item in self:
            item.isroldireccion = False
    
    
    def getMeteo(self):
        self.indicativometeo = self.indicativometeo.replace(" ","")
        indicativos = self.indicativometeo.split(',')
        horallegadaprevista = self.horallegadaprevista
        horallegada = self.horallegada
        horasalida = self.utc_horasalida
        fechavuelo = self.fechavuelo
        estado = self.estado
        timestampstart = None
        
        # strhoraend = utilitylib.leulit_float_time_to_str(horasalida)
        tira = ("{0} {1}").format(fechavuelo, horasalida)
        timpestampend = datetime.strptime(tira, "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M:%S+0000")

        # strhorastart = utilitylib.leulit_float_time_to_str(horasalida)
        tira = ("{0} {1}").format(fechavuelo, horasalida)
        objtimestart = datetime.strptime(tira, "%Y-%m-%d %H:%M") - timedelta(hours=1)
        timestampstart = objtimestart.strftime("%Y-%m-%dT%H:%M:%S+0000")

        meteotext = []
        for indicativo in indicativos:
            try:
                indicativo = indicativo.upper()
                url = "https://www.aviationweather.gov/cgi-bin/data/dataserver.php?dataSource=metars&requestType=retrieve&format=xml&startTime={0}&endTime={1}&stationString={2}"
                url = (url).format(timestampstart,timpestampend,indicativo)
                _logger.error('getmeteo --> %r',url)
                response = urllib3.PoolManager().request("GET",url)
                reddit = etree.fromstring(response.data)
                meteotext.append( ("Indicativo {0}\n").format( indicativo ) )
                for item in reddit.xpath('/response/data/METAR'):
                    raw_text = item.xpath("./raw_text/text()")[0]
                    observation_time = item.xpath("./observation_time/text()")[0]
                    temp_c = item.xpath("./temp_c/text()")[0]
                    wind_dir_degrees = item.xpath("./wind_dir_degrees/text()")[0]
                    wind_speed_kt = item.xpath("./wind_speed_kt/text()")[0]
                    visibility_statute_mi = item.xpath("./visibility_statute_mi/text()")[0]
                    flight_category = item.xpath("./flight_category/text()")[0] if item.xpath("./flight_category/text()") else ""
                    elevation_m = item.xpath("./elevation_m/text()")[0]
                    try:
                        sky_cover = item.find("./sky_condition").attrib['sky_cover']
                    except Exception as e:
                        sky_cover = ''

                    try:
                        cloud_base_ft_agl = item.find("./sky_condition").attrib['cloud_base_ft_agl']
                    except Exception as e:
                        cloud_base_ft_agl = ''

                    tira = "{0}\n" \
                            "Time: {1}\n" \
                            "Temperature: {2}\n" \
                            "Wind dir degrees: {3}\n" \
                            "Wind speed: {4} kt" \
                            "Visibility Statute: {5} mi\n" \
                            "Flight category: {6}\n" \
                            "Elevation: {7} mi\n" \
                            "Sky cover: {8}\n" \
                            "Cloud base ft agl: {9}\n" \
                            "-----------------------\n"
                    tira = (tira).format(raw_text, observation_time,temp_c,wind_dir_degrees,wind_speed_kt,visibility_statute_mi,flight_category,elevation_m,sky_cover,cloud_base_ft_agl)
                    meteotext.append(tira)
                meteotext.append("\n\n==============================\n\n")
            except urllib3.exceptions.HTTPError as e:
                meteotext.append(("{0}\n{1}").format(indicativo, e.read()))
        meteotext = "".join(meteotext)
        self.meteo = meteotext

    
    
    @api.onchange('helicoptero_id')
    def onchange_helicoptero(self):
        warning = {}
        for item in self:
            if item.helicoptero_id:
                if self.isHelicopterBlocked(item.helicoptero_id.id, item.fechavuelo):
                    warning = {
                        'title': _("Warning"),
                        'message': _('Este helicoptero tiene una anomalía/discrepancia sin firmar y no puede ser utilizado'),
                    }
                    return {
                        'warning' : warning
                    }
                
                # ACTUALIZAR TACOM DE SALIDA
                vuelos = self.search([('helicoptero_id', "=", item.helicoptero_id.id),('estado','=','cerrado'),('fechasalida','!=',False)],limit=1 ,order='fechasalida desc')
                tacomsalida = 0
                editfuelrem = 0
                lugarllegada = False
                for vuelo in vuelos:
                    tacomsalida = vuelo.tacomllegada
                    editfuelrem = vuelo.fuelllegada
                    lugarllegada = vuelo.lugarllegada
                obj_perf = item.performance
                values = {
                    'emptyweight'            : item.helicoptero_id.emptyweight,
                    'longmoment'             : item.helicoptero_id.longmoment,
                    'latmoment'              : item.helicoptero_id.latmoment,
                    'longarm'                : item.helicoptero_id.longarm,
                    'latarm'                 : item.helicoptero_id.latarm,
                    'pesomax'                : item.helicoptero_id.pesomax,
                    'helicoptero_modelo'     : item.helicoptero_id.modelo.name,
                    'helicoptero_tipo'       : item.helicoptero_id.tipo,
                    'velocidadprevista'      : round(item.helicoptero_id.velocidad,2),
                    'fuelremanente'          : editfuelrem,
                    'editfuelrem'            : editfuelrem,
                    'fuelsalida'             : editfuelrem,
                    'combustibleextra'       : editfuelrem,
                    'consumomedio_vuelo'     : item.helicoptero_id.consumomedio,
                    'performance'            : None,
                    'lugarsalida'            : lugarllegada,
                    'tacomsalida'            : tacomsalida,
                }
                item.write(values)
                obj_perf.unlink()
                return { 'value' : values }
    

    @api.onchange('doblemando')
    def on_change_doblemando(self):
        vals={}
        for item in self:
            if item.doblemando == True:
                item.asiento_pic = "pic_left"
            else:
                item.asiento_pic = "pic_right"


    @api.onchange('ruta_id')
    def onchange_ruta(self):
        new_aerovia_ids = []
        vuelos = self
        for vuelo in vuelos:
            for aerovia in vuelo.aerovia_ids:
                new_aerovia_ids.append((2, aerovia.id))
        distanciatotal = 0
        tiempo_previsto_total = 0
        for av in self.ruta_id.aerovia_ids:
            distanciatotal += av.distancia
            tp = utilitylib.get_tiempo_vuelo_decimal( float(av.distancia), self.velocidadprevista )
            tiempo_previsto_total += round(tp,2)
            new_aerovia_ids.append((0,0,{
                'ruta_id': self.ruta_id.id,
                'aerovia_id' : av.aerovia_id.id,
                'aerovia_ruta_id' : av.id,
                'vuelo_id': self.id,
                'tiempoprevisto': round(tp,2)}))
        if (self.ruta_id):
            vals = {
                'aerovia_ids'                   : new_aerovia_ids,
                'tiempoprevisto'                : tiempo_previsto_total,
                'distanciatotalprevista'        : round(distanciatotal,2),
            }
            res = { 'value' : vals }
        else:
            res =  {}
        return res

    @api.onchange('velocidadprevista')
    def oc_velocidadprevista(self):
        for item in self:
            return item.calculosFuel('velocidadprevista')

    @api.onchange('horallegadaprevista')
    def oc_horallegadaprevista(self):
        for item in self:
            return item.calculosFuel('horallegadaprevista')

    @api.onchange('distanciatotalprevista')
    def oc_distanciatotalprevista(self):
        for item in self:
            return item.calculosFuel('distanciatotalprevista')

    @api.onchange('tiempoprevisto')
    def oc_tiempoprevisto(self):
        for item in self:
            return item.calculosFuel('tiempoprevisto')

    @api.onchange('horasalida')
    def oc_horasalida(self):
        for item in self:
            return item.calculosFuel('horasalida')

    @api.onchange('reservasfuel')
    def oc_reservasfuel(self):
        for item in self:
            return item.calculosFuel('reservasfuel')

    @api.onchange('consumomedio_vuelo')
    def oc_consumomedio_vuelo(self):
        for item in self:
            return item.calculosFuel('consumomedio_vuelo')

    @api.onchange('rodaje')
    def oc_rodaje(self):
        for item in self:
            return item.calculosFuel('rodaje')

    @api.onchange('contingencia')
    def oc_contingencia(self):
        for item in self:
            return item.calculosFuel('contingencia')

    @api.onchange('distancia_alternativo')
    def oc_distancia_alternativo(self):
        for item in self:
            return item.calculosFuel('distancia_alternativo')

    @api.onchange('helicoptero_tipo')
    def oc_helicoptero_tipo(self):
        for item in self:
            return item.calculosFuel('helicoptero_tipo')

    @api.onchange('editfuelrem')
    def oc_editfuelrem(self):
        for item in self:
            return item.calculosFuel('editfuelrem')

    @api.onchange('fuelqty')
    def oc_fuelqty(self):
        for item in self:
            return item.calculosFuel('fuelqty')

    @api.onchange('fuelllegada')
    def oc_fuelllegada(self):
        for item in self:
            return item.calculosFuel('fuelllegada')
       
    def calculosFuel(self, field):
        vuelo = None
        valores = {}
        for item in self:
            vuelo = item
        if field == 'velocidadprevista' or field == 'distanciatotalprevista':
            if not vuelo.ruta_id:
                result = utilitylib.get_tiempo_vuelo_decimal(vuelo.distanciatotalprevista, vuelo.velocidadprevista)
                vuelo.tiempoprevisto = round(result, 2)
        if field == 'tiempoprevisto':
            vv = utilitylib.convert_nudos_metros_por_segundo(vuelo.velocidadprevista)
            if vuelo and not vuelo.ruta_id.id:
                distanciatotalprevista = (vv * (vuelo.tiempoprevisto * 3600))
                distanciatotalprevista = utilitylib.convert_metros_nauticmiles(distanciatotalprevista)
                vuelo.distanciatotalprevista = round(distanciatotalprevista, 2)

        combustibleminimo = self._calc_combustible_minimo(
            vuelo.tiempoprevisto, 
            vuelo.reservasfuel, 
            vuelo.consumomedio_vuelo, 
            vuelo.rodaje, 
            vuelo.contingencia, 
            vuelo.distancia_alternativo, 
            vuelo.velocidadprevista
        )

        fuelsalida = self._calc_fuelsalida(vuelo.editfuelrem, vuelo.fuelqty)

        combustibleextra = fuelsalida - combustibleminimo
        
        vuelo.horallegadaprevista = vuelo.horasalida + vuelo.tiempoprevisto

        minutosprevistos = utilitylib.leulit_float_time_to_minutes(vuelo.tiempoprevisto)
        fuellanding = fuelsalida - (vuelo.consumomedio_vuelo * minutosprevistos)

        #valores['combustibleminimo'] = combustibleminimo
        vuelo.combustibleminimo = combustibleminimo
        vuelo.combustibleminimo_kg = utilitylib.convert_litros_to_kg(combustibleminimo, vuelo.helicoptero_tipo)
        vuelo.combustibleminimo_gal = utilitylib.convert_litros_to_gal(combustibleminimo, vuelo.helicoptero_tipo)
        vuelo.fuelsalida = fuelsalida
        vuelo.fuelsalida_kg = utilitylib.convert_litros_to_kg(fuelsalida, vuelo.helicoptero_tipo)
        vuelo.fuelsalida_kg = utilitylib.convert_litros_to_kg(fuelsalida, vuelo.helicoptero_tipo)
        vuelo.fuelsalida_gal = utilitylib.convert_litros_to_gal(fuelsalida, vuelo.helicoptero_tipo)
        vuelo.combustiblelanding = fuellanding
        vuelo.combustiblelanding_kg = utilitylib.convert_litros_to_kg(fuellanding, vuelo.helicoptero_tipo)
        vuelo.combustiblelanding_gal = utilitylib.convert_litros_to_gal(fuellanding, vuelo.helicoptero_tipo)
        vuelo.combustibleextra = combustibleextra
        vuelo.combustibleextra_kg = utilitylib.convert_litros_to_kg(combustibleextra, vuelo.helicoptero_tipo)
        vuelo.combustibleextra_gal = utilitylib.convert_litros_to_gal(combustibleextra, vuelo.helicoptero_tipo)
        vuelo.fuelremanente_gal = utilitylib.convert_litros_to_gal(vuelo.editfuelrem, vuelo.helicoptero_tipo)
        vuelo.fuelremanente_gal = utilitylib.convert_litros_to_gal(vuelo.editfuelrem, vuelo.helicoptero_tipo)
        vuelo.fuelremanente_kg = utilitylib.convert_litros_to_kg(vuelo.editfuelrem, vuelo.helicoptero_tipo)
        vuelo.fuelqty_gal = utilitylib.convert_litros_to_gal(vuelo.fuelqty, vuelo.helicoptero_tipo)
        vuelo.fuelqty_kg = utilitylib.convert_litros_to_kg(vuelo.fuelqty, vuelo.helicoptero_tipo)
        
        # vuelo.fuelllegada = fuellanding
        vuelo.fuelllegada_kg = utilitylib.convert_litros_to_kg(vuelo.fuelllegada, vuelo.helicoptero_tipo)
        vuelo.fuelllegada_gal = utilitylib.convert_litros_to_gal(vuelo.fuelllegada, vuelo.helicoptero_tipo)
        vuelo.combustiblelanding = fuellanding
        vuelo.combustiblelanding_kg = utilitylib.convert_litros_to_kg(vuelo.combustiblelanding, vuelo.helicoptero_tipo)
        vuelo.combustiblelanding_gal = utilitylib.convert_litros_to_gal(vuelo.combustiblelanding, vuelo.helicoptero_tipo)
        vuelo.consumomedio_vuelo_kg = utilitylib.convert_litros_to_kg(vuelo.consumomedio_vuelo, vuelo.helicoptero_tipo)
        vuelo.consumomedio_vuelo_gal = utilitylib.convert_litros_to_gal(vuelo.consumomedio_vuelo, vuelo.helicoptero_tipo)

        vuelo.combustibletrayecto = self._calc_combustible_trayecto(vuelo.tiempoprevisto, vuelo.consumomedio_vuelo)
        vuelo.combustibletrayecto_kg = utilitylib.convert_litros_to_kg(vuelo.combustibletrayecto, vuelo.helicoptero_tipo)
        vuelo.combustibletrayecto_gal = utilitylib.convert_litros_to_gal(vuelo.combustibletrayecto, vuelo.helicoptero_tipo)
        if vuelo.estado == 'prevuelo' and field != 'horasalida' and  field != 'horallegadaprevista':
            vuelo.weight_and_balance_id = False
            vuelo.performance = False
        return {
            'values' : valores
        }

    def _calc_combustible_minimo(self, tiempoprevisto, reservasfuel, consumomedio_vuelo, rodaje, contingencia, distancia_alternativo, velocidadprevista):
        if not rodaje:
            rodaje = 0
        if not contingencia:
            contingencia = 0
        if not distancia_alternativo:
            distancia_alternativo = 0
        tiempo_a_alternativo = utilitylib.get_tiempo_vuelo_decimal(distancia_alternativo, velocidadprevista)
        rodaje = utilitylib.leulit_str_to_float_time( utilitylib.leulit_float_minutes_to_str( float(rodaje) ) )
        tiempo = tiempoprevisto + rodaje + tiempo_a_alternativo
        if contingencia == '5':
            tiempo = tiempo * ((float(contingencia)/100) + 1)
        minutosprevistos = utilitylib.leulit_float_time_to_minutes(tiempo)
        combustibleminimo = consumomedio_vuelo * (minutosprevistos+float(reservasfuel))
        return round(combustibleminimo,2)

    def _calc_fuelsalida(self, remanente, fuelqty):
        return round((remanente + fuelqty),2)

    @api.onchange('oilqty')
    def on_change_oilqty(self):
        kilos =  utilitylib.convert_litros_to_kg( self.oilqty, self.helicoptero_tipo )
        galones = utilitylib.convert_litros_to_gal( self.oilqty, self.helicoptero_tipo )
        return {'value':
            {
                'oilqty_kg': kilos,
                'oilqty_gal': galones,
            }
        }
    
    def _calc_fuelllegada(self, tiemposervicio, fuelsalida, consumomedio_vuelo):
        minutosprevistos = utilitylib.leulit_float_time_to_minutes(tiemposervicio)
        return round((fuelsalida - (consumomedio_vuelo * minutosprevistos)),2)

    @api.onchange('tiemposervicio')
    def updateHoraLlegada(self):
        valor = (self.horasalida + self.tiemposervicio)
        fuellanding = self._calc_fuelllegada(self.tiemposervicio, self.fuelsalida, self.consumomedio_vuelo)

        return {
            'value': {
                'horallegada'   : valor,
                'fuelllegada'   : fuellanding,
            }
        }
    
    def getNotam(self):
        self.notam_revisado = True
        self.notaminfo = self.getNotamInfo()

    def getNotamInfo(self):
        s = ""
        url = "https://applications.icao.int/dataservices/api/notams-list?api_key=53087205-79b5-4b01-91a2-ca7b727e2131&format=json&criticality=&states=ESP"
        import json
        import requests
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry

        try:
            session = requests.Session()
            retry = Retry(connect=1, backoff_factor=0.5)
            adapter = HTTPAdapter()
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            r = session.get(url)
            for item in r.json():
                s = s + """
                        <p>
                            <b>id:&nbsp;</b>{0} | <b>status:&nbsp;</b>{1}<br/>
                            <b>message:&nbsp;</b>{2}<br/>
                            <b>startdate:&nbsp;</b>{3}<br/>
                            <b>enddate:&nbsp;</b>{4}<br/>
                            <b>location:&nbsp;</b>{5}<br/>
                            <b>Condition:&nbsp;</b>{6}<br/>
                        </p>
                    <hr/>
                """.format(item['id'],item['status'],item['message'],item['startdate'],item['enddate'],item['location'],item['Condition'])
        except Exception as e:
            import sys
            ex_type, ex_value, ex_traceback = sys.exc_info()
            s = "ERROR AL DESCARGAR NOTAM : {1}  --- {0}".format(ex_value,ex_traceback)
        return s
        
    def _get_tipo_actividad(self):
        for item in self:
            tipo_actividad = None
            nombre_actividad = ''
            rel_tipovuelo = self.env['leulit.vuelo_tipo_line'].search([('vuelo_id','=',item.id)])
            if rel_tipovuelo.ids and len(rel_tipovuelo.ids) > 0:
                tipo_actividad= rel_tipovuelo[0].vuelo_tipo_id.tipo_trabajo
                nombre_actividad = rel_tipovuelo[0].vuelo_tipo_id.name
            item.tipo_actividad = tipo_actividad
            item.nombre_actividad = nombre_actividad

    @api.depends('horasalida')
    def _strhorasalida(self):
        tira = ""
        valor = 0
        for item in self:
            valor = item.horasalida
            tira = utilitylib.hlp_float_time_to_str( valor )
            item.strhorasalida = tira

    @api.depends('horallegada')
    def _strhorallegada(self):
        tira = ""
        valor = 0
        for item in self:
            valor = item.horallegada
            tira = utilitylib.hlp_float_time_to_str( valor )
            item.strhorallegada = tira

    @api.depends('tiemposervicio')
    def _strtiemposervicio(self):
        for item in self:
            valor = item.tiemposervicio
            tira = utilitylib.hlp_float_time_to_str( valor )
            item.strtiemposervicio = tira
            
    @api.depends('tiempoprevisto')
    def _strtiempoprevisto(self):
        for item in self:
            valor = item.tiempoprevisto
            tira = utilitylib.hlp_float_time_to_str( valor )
            item.strtiempoprevisto = tira            
    
    @api.depends('airtime')
    def _strairtime(self):
        tira = ""
        res = {}
        valor = 0
        for item in self:
            valor = item.airtime
            tira = utilitylib.hlp_float_time_to_str( valor )
            item.strairtime = tira

    @api.depends('deltahoras')
    def _strdeltahoras(self):
        tira = ""
        res = {}
        valor = 0
        for item in self:
            valor = item.deltahoras
            tira = utilitylib.hlp_float_time_to_str( valor )
            item.strdeltahoras = tira

    @api.depends('fuelsalida','consumomedio_vuelo','tiempoprevisto')
    def _calc_tiempo_vuelo_max(self):        
        for item in self:
            minutosprevistos = utilitylib.hlp_float_time_to_minutes(item.tiempoprevisto)
            valor = item.fuelsalida / item.consumomedio_vuelo
            if valor < 0 :
                valor = 0
            item.tiempo_vuelo_max = utilitylib.hlp_float_minutes_to_str( valor )

    def _tiempo_ato(self):
        for item in self:
            valor = 0.0
            if item.silabus_ids:
                for silabus in item.silabus_ids:
                    if silabus.rel_curso:
                        for curso in silabus.rel_curso:
                            if curso.ato_mi:
                                valor = item.tiemposervicio
            item.tiempo_ato = valor

    def _tiempo_ato_mo(self):
        for item in self:
            valor = 0.0
            if item.silabus_ids:
                for silabus in item.silabus_ids:
                    if silabus.rel_curso:
                        for curso in silabus.rel_curso:
                            if curso.ato_mo:
                                valor = item.tiemposervicio
            item.tiempo_ato_mo = valor

    def _tiempo_lci(self):
        for item in self:
            valor = 0.0
            if item.silabus_ids:
                for silabus in item.silabus_ids:
                    if silabus.rel_curso:
                        for curso in silabus.rel_curso:
                            if curso.lci:
                                valor = item.tiemposervicio
            item.tiempo_lci = valor

    def _tiempo_aoc(self):
        for item in self:
            valor = 0.0
            if item.silabus_ids:
                for silabus in item.silabus_ids:
                    if silabus.rel_curso:
                        for curso in silabus.rel_curso:
                            if curso.aoc:
                                valor = item.tiemposervicio
            item.tiempo_aoc = valor

    @api.depends('horallegada','fechavuelo','lugarllegada')
    def _utc_horallegada(self):
        for item in self:
            valor = 0.0
            if item.horallegada and item.lugarllegada and item.fechavuelo:
                valor = utilitylib.getStrTimeUTC(item.fechavuelo, item.horallegada, item.lugarllegada.tz)
            item.utc_horallegada = valor

    @api.depends('horasalida','fechavuelo','lugarsalida')
    def _utc_horasalida(self):
        for item in self:
            valor = 0.0
            if item.horasalida and item.lugarsalida and item.fechavuelo:
                valor = utilitylib.getStrTimeUTC(item.fechavuelo, item.horasalida, item.lugarsalida.tz)
            item.utc_horasalida = valor     

    @api.depends('horallegadaprevista','fechavuelo','lugarllegada')
    def _utc_horallegadaprevista(self):
        for item in self:
            valor = 0.0
            if item.horallegadaprevista and item.lugarsalida and item.fechavuelo:
                valor = utilitylib.getStrTimeUTC(item.fechavuelo, item.horallegadaprevista, item.lugarllegada.tz)
            item.utc_horallegadaprevista = valor 
                   
    def _tiempo_instuctor_actividad(self):
        for item in self:
            item.tiempo_instuctor_actividad = item.tiempo_aoc + item.tiempo_lci + item.tiempo_ato_mo
    
    @api.depends('fechavuelo','helicoptero_id')
    def _calc_delta_landings(self):
        for item in self:
            asset_ids_def = []
            asset_ids = self.search([('estado','=','cerrado'),('fechavuelo', '<=', item.fechavuelo), ('helicoptero_id', '=', item.helicoptero_id.id )])
            for vuelo in asset_ids:
                if vuelo.fechavuelo < item.fechavuelo:
                    asset_ids_def.append(vuelo)
                else:
                    if vuelo.horallegada <= item.horallegada:
                        asset_ids_def.append(vuelo)
            landings = 0
            for vuelo in asset_ids_def:
                landings = landings + vuelo.landings + vuelo.nightlandings
            item.deltalandings = landings

    @api.depends('horasalida','airtime')
    def _calc_horallegada_airtime(self):
        for item in self:
            valor = item.horasalida + item.airtime
            tira = utilitylib.leulit_float_time_to_str( valor )
            item.strhorallegadaairtime = tira

    @api.depends('fechavuelo','helicoptero_id')
    def _calc_delta_horas_motor(self):
        for item in self:
            horas = 0.0
            if item.fechavuelo and item.helicoptero_id:
                datosMotor = self.env['leulit.helicoptero_pieza'].get_datos_motor_instalado_in_fecha(item.helicoptero_id.id, item.fechavuelo)
                if datosMotor and datosMotor.from_date:
                    datos = self.acumulados_between_date_and_datetime(item.helicoptero_id.id, datosMotor.from_date, item.fechasalida)
                    horas = datos['suma_airtime'] + datosMotor['horas_inicio']
            item.deltahorasmotor = horas
    
    @api.depends('deltahorasmotor')
    def _get_str_deltahorasmotor(self):
        for item in self:
            item.strdeltahorasmotor = utilitylib.leulit_float_time_to_str( item.deltahorasmotor )

    def getDateTimeUTC(self, fecha, hora, tz):
        try:
            date2 = utilitylib.leulit_float_time_to_str( hora )
            date1 = fecha.strftime("%Y-%m-%d")
            tira =  date1+" "+date2
            valor = datetime.strptime(tira,"%Y-%m-%d %H:%M")
            madrid_tz = pytz.timezone(tz)
            mtz = madrid_tz.localize(datetime(valor.year, valor.month, valor.day, valor.hour, valor.minute))
            dt_utc = mtz.astimezone(pytz.timezone('UTC'))
            return dt_utc.replace(tzinfo=None)
        except Exception as e:
            _logger.error("_date_end_utc %r",e)
            return None            

    def _date_start_utc(self):
        try:
            for item in self:
                valor = self.getDateTimeUTC( item.fechavuelo, item.horasalida, item.lugarsalida.tz)
                item.date_start_utc = valor
        except Exception as e:
            _logger.error("_date_start_utc %r",e)
            item.date_start_utc = None            

    def _date_end_utc(self):
        try:
            for item in self:
                valor = self.getDateTimeUTC( item.fechavuelo, item.horallegada, item.lugarllegada.tz)
                item.date_end_utc = valor
        except Exception as e:
            _logger.error("_date_end_utc %r",e)
            item.date_end_utc = None

    @api.model
    def wizardSetPrevuelo(self):
        self.p_corregido = True
        self.estado = 'prevuelo'
    
    @api.depends('fechasalida', 'helicoptero_id')
    def check_first_flight(self):
        if self.helicoptero_tipo in ('EC120B', 'CABRI G2'):
            vuelos_anteriores = self.search([
                ('estado', '=', 'cerrado'),
                ('fechavuelo', '=', self.fechavuelo),
                ('helicoptero_id', '=', self.helicoptero_id.id),
            ], order='fechavuelo desc', limit=1)
            if vuelos_anteriores:
                if self.fechasalida > vuelos_anteriores.fechasalida:
                    if not self.checklist_prevuelo_entre_vuelos:
                        raise UserError('Este helicóptero ya ha tenido un vuelo hoy. Se debe hacer la inspección entre vuelos. Vuelo anterior: {}'.format(vuelos_anteriores.codigo))
            else:
                if not self.checklist_prevuelo_BFF:
                    raise UserError('Primer vuelo de este helicóptero hoy. Se debe hacer la inspección prevuelo BFF')

    @api.onchange('checklist_prevuelo_BFF')
    def select_entrevuelo(self):
        if self.checklist_prevuelo_BFF:
            self.checklist_prevuelo_entre_vuelos = False  
        else:
            self.checklist_prevuelo_entre_vuelos = True
            
    @api.onchange('checklist_prevuelo_entre_vuelos')
    def select_BFF(self):
        if self.checklist_prevuelo_entre_vuelos:
            self.checklist_prevuelo_BFF = False
        else:
            self.checklist_prevuelo_BFF = True
        
    
    @api.onchange('verificado')
    def cambio_numtripulantes_verificado(self):
        if self.verificado: 
            self.numtripulacion = 2
        else:
            self.numtripulacion = 1

    @api.depends('fechavuelo')
    def _is_last_30_days(self):
        for item in self:
            if item.fechavuelo:
                fecha = datetime.strptime(item.fechavuelo, "%Y-%m-%d")
                fecha_actual = datetime.now().date()
                diferencia = fecha_actual - fecha
                if diferencia.days <= 30:
                    return True
        return False

    def _search_is_last_30_days(self, operator, value):
        """
        Método de búsqueda para el campo is_last_30_days.
        Devuelve un dominio que filtra los registros según si están dentro de los últimos 30 días.
        """
        today = fields.Date.context_today(self)
        last_30_days = today - timedelta(days=30)
        if operator == '=' and value:
            # Filtrar registros cuya fecha de vuelo está dentro de los últimos 30 días
            return [('fechavuelo', '>=', last_30_days)]
        elif operator == '=' and not value:
            # Filtrar registros cuya fecha de vuelo está fuera de los últimos 30 días
            return [('fechavuelo', '<', last_30_days)]
        else:
            raise ValueError("Operador no soportado para el campo is_last_30_days")


    p_corregido = fields.Boolean(string="Parte corregido", default=False)
    codigo = fields.Char('Código', size=20)
    fechavuelo = fields.Date('Fecha', required=True, default=fields.Date.context_today)
    fuelqty = fields.Float('Combustible añadido (l.)', help='Cantidad combustible añadida antes de iniciar el vuelo (en litros)')
    fuelqty_kg = fields.Float('')
    fuelqty_gal = fields.Float('')
    fuelremanente = fields.Float(compute=_get_combustible_remanente,string='Fuel remanente (l.)')
    fuelremanente_kg = fields.Float('')
    fuelremanente_gal = fields.Float('')
    editfuelrem = fields.Float('Fuel remanente (l.)')
    oilqty = fields.Float('Aceite añadido (l.)',default=-1)
    oilqty_kg = fields.Float('')
    oilqty_gal = fields.Float('',default=-0.26)
    meteo = fields.Text('Meteorología')
    indicativometeo = fields.Char('Indicativo meteo')
    notam = fields.Binary('Notam')
    notamfilename = fields.Char("Nombre fichero notam", type='string')
    notaminfo = fields.Html("Notam info")
    notam_revisado = fields.Boolean('Notam revisado')
    notneednotam = fields.Boolean('Verificado')
    descnotneednotam = fields.Selection([('vuelo-local', 'Vuelo local'),('otros', 'Otros')], 'Motivo')
    vuelo_tipo_line = fields.One2many('leulit.vuelo_tipo_line', 'vuelo_id', 'Tipo Vuelo')
    vuelo_tipo_main = fields.Char(compute=_get_vuelo_tipo_main,string='Vuelo Tipo Main',search=_search_vuelo_tipo_main)
    numpax = fields.Integer('Nº de pax / AESA', help='Numero de pasajeros')
    numtripulacion = fields.Integer('Nº tripulantes',default=1)
    cg = fields.Char('C.G.', size=5)
    tow = fields.Float('Peso al despegue (kg.)')
    fechasalida = fields.Datetime(compute=_calc_fecha_salida,string='Fecha Salida', store=True)
    strfechasalida = fields.Char(compute=_calc_fecha_salida,string='Fecha Salida')
    horasalida = fields.Float('Hora salida local', required=True)
    strhorasalida = fields.Char(compute=_strhorasalida,string='Horas Salida')
    alternativos = fields.One2many('leulit.helipuerto', 'vuelo_id', string='Alternativos')
    lugarsalida = fields.Many2one('leulit.helipuerto', 'Helipuerto salida', required=False)
    fuelsalida = fields.Float('Combustible salida (l.)')
    fuelsalida_kg = fields.Float('')
    fuelsalida_gal = fields.Float('')
    reservasfuel = fields.Selection([('10','10 min.'),('20','20 min.'),('30','30 min.')],'Reserva fuel',default='30')
    rodaje = fields.Selection([('0', '0 min.'),('2', '2 min.'), ('5', '5 min.')], 'Rodaje',default='0')
    contingencia = fields.Selection([('0', '0 %'),('5', '5 %')], 'Contingencia',default='0')
    distancia_alternativo = fields.Float('Distancia alternativo')
    tacomsalida = fields.Float('Tacom. salida', help='R22/R44 Tacómetro salida')
    strhorallegada = fields.Char(compute=_strhorallegada,string='Hora llegada local')
    horallegada = fields.Float(string='Hora llegada local')
    fechallegada = fields.Datetime(compute=_calc_fecha_llegada,string='Fecha Llegada', store=False)
    strfechallegada = fields.Char(compute=_calc_fecha_llegada,string='Fecha Llegada', store=False)
    strhorallegadaairtime = fields.Char(compute=_calc_horallegada_airtime,string='Hora llegada airtime')
    lugarllegada = fields.Many2one('leulit.helipuerto', 'Helipuerto llegada', required=True)
    fuelllegada = fields.Float(string='Combustible llegada (l.)')
    fuelllegada_kg = fields.Float('')
    fuelllegada_gal = fields.Float('')
    tacomllegada = fields.Float('Tacom. Llegada', help='R22/R44 Tacómetro llegada')
    ngvuelo = fields.Float('NG vuelo', help='EC120B NG del vuelo')
    nfvuelo = fields.Float('NF vuelo', help='EC120B NF del vuelo')
    landings = fields.Integer('Day Landings',default=1)
    nightlandings = fields.Integer('Night Landings',default=0)
    deltalandings = fields.Integer(compute=_calc_delta_landings,string='Delta landings')
    tiempoprevisto = fields.Float('Tiempo de vuelo previsto', required=True)
    strtiempoprevisto = fields.Char(compute=_strtiempoprevisto,string='Tiempo previsto')
    horallegadaprevista = fields.Float(string='Hora llegada prevista local')
    tiemposervicio = fields.Float('Tiempo servicio')
    airtime = fields.Float('Air Time')
    strtiemposervicio = fields.Char(compute=_strtiemposervicio,string='Tiempo servicio')
    strairtime = fields.Char(compute=_strairtime,string='Air time')
    deltahoras = fields.Float(compute='_calc_delta_horas',string='Delta tacom salida')
    strdeltahoras = fields.Char(compute=_strdeltahoras,string='Delta airtime' , store=False)
    deltahorasmotor = fields.Float(compute='_calc_delta_horas_motor',string='Delta horas motor',store=False)
    strdeltahorasmotor = fields.Char(compute='_get_str_deltahorasmotor',string='Delta horas motor',store=False)
    helicoptero_id = fields.Many2one('leulit.helicoptero', string='Helicóptero', required=True, domain="[('baja','=',False)]")
    helicoptero_modelo = fields.Char(compute=_get_modelo_helicoptero,string="Modelo")
    helicoptero_tipo = fields.Selection(related='helicoptero_id.tipo',string='Tipo',store=True)
    strhoras_remanente = fields.Char(related='helicoptero_id.strhoras_remanente', string='Potencial Aeronave')
    semaforo = fields.Char(related='helicoptero_id.semaforo', string='Estado Aeronave')
    ruta_id = fields.Many2one('leulit.ruta', 'Ruta', domain=[('activo','=',True)])
    aerovia_ids = fields.One2many(comodel_name='leulit.rel_planoperacional_aerovia', inverse_name='vuelo_id', string='Aerovías')
    velocidadprevista = fields.Float(string='Velocidad prevista (KT)')
    distanciatotalprevista = fields.Float('Distancia Total prevista (NM)')
    piloto_supervisor_id = fields.Many2one('leulit.piloto', 'Piloto supervisor')
    piloto_id = fields.Many2one('leulit.piloto', 'PIC', required=True)
    peso_piloto = fields.Float(related='piloto_id.peso_piloto',string='Peso piloto')
    operador = fields.Many2one('leulit.operador', 'Operador')
    verificado = fields.Many2one('leulit.piloto', 'Verificado')
    weight_and_balance_id = fields.Many2one('leulit.weight_and_balance', 'Weight and Balance',ondelete="cascade")
    valid_takeoff_longcg = fields.Boolean(related='weight_and_balance_id.valid_takeoff_longcg',string='Valid TakeOff Long. CG',store=False)
    valid_takeoff_latcg = fields.Boolean(related='weight_and_balance_id.valid_takeoff_latcg',string='Valid TakeOff Lat. CG',store=False)
    valid_landing_longcg = fields.Boolean(related='weight_and_balance_id.valid_landing_longcg',string='Valid Landing Long. CG',store=False)
    valid_landing_latcg = fields.Boolean(related='weight_and_balance_id.valid_landing_latcg',string='Valid Landing Lat. CG',store=False)
    takeoff_gw = fields.Float(related='weight_and_balance_id.takeoff_gw',string='Take off gw',store=False)
    emptyweight = fields.Float('Peso en vacío (kg.)')
    longmoment = fields.Float('Long moment (cm/kg)')
    latmoment = fields.Float('Lat. moment (cm/kg)')
    longarm = fields.Float('Long moment (cm)')
    latarm = fields.Float('Lat. moment (cm)')
    pesomax = fields.Float(related='helicoptero_id.pesomax',string='Peso máximo (kg.)',store=True)
    wbdata = fields.Text('Weight & Balance Data')
    wbimage = fields.Binary('Weight & Balance Image')
    wbtipocalculopasajeros = fields.Selection([('Masa pesada','Masa pesada'),('Masa declarada','Masa declarada'),('Masa estandard','Masa estandard')], 'Cálculo peso pasajeros')
    wbokey = fields.Boolean('Weight & Balance',default=False)
    estado = fields.Selection([('prevuelo','Pre-Vuelo'),('postvuelo','Post-Vuelo'),('cerrado','Cerrado'),('cancelado','Cancelado')], 'Estado', default="prevuelo")
    comentarios = fields.Text('Comentarios')
    pasajero_ids = fields.Many2many('leulit.pasajero','pasajero_vuelo_rel', 'vuelo_id', 'pasajero_id', string="Pasajeros")
    velocidad = fields.Float(related='helicoptero_id.velocidad',string='Velocidad crucero (KT)',store=True)
    consumomedio_vuelo = fields.Float('Consumo medio (l/m)')
    consumomedio_vuelo_kg = fields.Float('')
    consumomedio_vuelo_gal = fields.Float('')
    combustibleminimo = fields.Float(string='Consumo mínimo (l.)')
    combustibleminimo_kg = fields.Float(string='Combustible mínimo (kg.)')
    combustibleminimo_gal = fields.Float(string='Combustible mínimo (gal.)')
    combustiblelanding = fields.Float(string='Combustible previsto aterrizaje (l.)')
    combustiblelanding_kg = fields.Float('')
    combustiblelanding_gal = fields.Float('')
    combustibleextra = fields.Float(string='Combustible extra (l.)')
    combustibleextra_kg = fields.Float(string='Combustible extra (kg.)')
    combustibleextra_gal = fields.Float(string='Combustible extra (gal.)')
    tiempo_vuelo_max = fields.Char(compute=_calc_tiempo_vuelo_max,string='Tiempo máximo de vuelo')
    curso_id = fields.Many2one('leulit.curso', 'Curso')
    vuelosolo_emergencia = fields.Boolean('Emergencias')
    vuelosolo_testvuelo = fields.Boolean('Test de vuelo')
    vuelosolo_autorizacion = fields.Boolean('Autorización')
    revisar = fields.Boolean('Revisar')
    motivorevision = fields.Text('Motivo')
    write_uid = fields.Many2one('res.users', 'by User')
    create_uid = fields.Many2one('res.users', 'created by User')
    nv = fields.Boolean('No Volado')
    # TODO Borrar campo isroldireccion
    isroldireccion = fields.Boolean(compute=_isroldireccion,string='Is rol direccion')
    asiento_pic = fields.Selection([('pic_right', 'PIC Asiento Derecha'),('pic_left', 'PIC Asiento Izquierda')], 'PIC Asiento',default='pic_right')
    ifr = fields.Boolean('IFR')
    night_hours = fields.Float(compute=_get_night_hours_vuelo,string='Night Hours',store=False)
    user_vuelo_ids = fields.Boolean(compute=_get_user_vuelo_ids,string='Usuarios',search=_search_user_vuelo_ids)
    is_comercial_uid = fields.Boolean(string='¿Is Comercial?', default=True)
    tipo_actividad = fields.Char(compute=_get_tipo_actividad,string='Tipo actividad', store=False) 
    nombre_actividad = fields.Char(compute=_get_tipo_actividad,string='Nombre actividad', store=True) 
    uso_gancho = fields.Float('Uso gancho')
    meteo_imprimir_report = fields.Boolean('Meteorologia',default=True)

    combustibletrayecto = fields.Float(compute=_get_combustibletrayecto,string="Combustible trayecto (l.)")
    combustibletrayecto_kg = fields.Float(compute=_get_combustibletrayecto,string="Combustible trayecto (kg)")
    combustibletrayecto_gal = fields.Float(compute=_get_combustibletrayecto,string="Combustible trayecto (gal)")
    foto_piloto = fields.Binary(related='piloto_id.image_128',string='Foto PIC',store=False)
    foto_operador = fields.Binary(related='operador.image_128',string='Foto operador',store=False)
    foto_verificado = fields.Binary(related='verificado.image_128',string='Foto verificado',store=False)
    foto_piloto_supervisor_id = fields.Binary(related='piloto_supervisor_id.image_128',string='Foto supervisor',store=False)
    presupuesto = fields.Many2one('sale.order','Presupuesto')
    presupuesto_str = fields.Char('Nombre presupuesto antiguo')
    presupuesto_old = fields.Integer('Id presupuesto antiguo')
    presupuestos = fields.Many2many('sale.order', 'vuelos_sale_order_rel','vuelo_id','so_id', string="Presupuestos")                
    checklist_realizado = fields.Boolean('Inspección prevuelo realizada')
    checklist_postvuelo_realizado = fields.Boolean('Inspección postvuelo realizada')
    checklist_prevuelo_BFF = fields.Boolean('Inspección prevuelo BFF realizada', default=True)
    checklist_prevuelo_entre_vuelos = fields.Boolean('Inspección prevuelo entre vuelos realizada')
    briefing_realizado = fields.Boolean('Briefing Aerodromo Salida, LLegada y Alternativos')
    numpae = fields.Integer('Num. AL/PA/PE/PAE/PO')
    tiempo_ato = fields.Float(compute=_tiempo_ato,string='Tiempo ATO MI',store=False)
    tiempo_ato_mo = fields.Float(compute=_tiempo_ato_mo,string='Tiempo ATO MO',store=False)
    tiempo_lci = fields.Float(compute=_tiempo_lci,string='Tiempo LCI',store=False)
    tiempo_aoc = fields.Float(compute=_tiempo_aoc,string='Tiempo AOC',store=False)
    tiempo_instuctor_actividad = fields.Float(compute=_tiempo_instuctor_actividad,string='Tiempo actividad',store=False)

    peso = fields.Float('Peso')
    temperatura = fields.Float('Temperatura')
    performance = fields.One2many('leulit.performance','vuelo','Performance')
    active = fields.Boolean(string="Activo",default=True)
    presupuesto_vuelo = fields.Many2one(comodel_name='sale.order', string='Presupuesto', domain=[('flag_flight_part','=',True),('state','=','sale'),('tag_ids','=',False),('task_done','=',False)])
    arlanding = fields.Integer(string='Autorotation Landings')
    
    # Fechas y horas UTC
    date_start_utc = fields.Datetime(compute=_date_start_utc,string="Fecha inicio UTC")
    date_end_utc = fields.Datetime(compute=_date_end_utc,string="Fecha fin UTC")

    utc_horallegada = fields.Char(compute=_utc_horallegada,string='Hora llegada UTC',store=False)
    utc_horasalida = fields.Char(compute=_utc_horasalida,string='Hora salida UTC',store=False)
    utc_horallegadaprevista = fields.Char(compute=_utc_horallegadaprevista,string='Hora llegada prevista UTC',store=False)

    sling_cycle = fields.Integer(string='Ciclo de Eslinga')

    # Equipos de Emergencia  
    balsa = fields.Boolean(string="Balsa")
    flotadores = fields.Boolean(string="Flotadores")
    chalecos = fields.Boolean(string="Chalecos")

    # Campo para restriccion de pasajeros
    pasajeros_wb = fields.Integer(string="Pasajeros en M&B")

    estado_vista = fields.Selection([
        ('prevuelo', 'Prevuelo'),
        ('fin_prevuelo', 'Fin prevuelo'),
        ('postvuelo', 'Postvuelo'),
        ('cerrado', 'Cerrado'),
        ('cancelado', 'Cancelado')
    ], 'Estado de Vista', default= 'prevuelo')
    is_last_30_days = fields.Boolean(compute=_is_last_30_days, string="En los últimos 30 días", search=_search_is_last_30_days)


    @api.constrains('airtime')
    def _check_airtime_multiple_of_6_minutes(self):
        for item in self:
            if not self._is_multiple_of_six_minutes(item.airtime):
                raise ValidationError("El Airtime debe ser múltiplo de 6 minutos.")

    @api.constrains('ngvuelo', 'nfvuelo')
    def _check_ng_nf(self):
        for item in self:
            if item.ngvuelo > 4:
                raise ValidationError("El NG del vuelo no puede ser mayor de 4.")
            if item.nfvuelo > 4:
                raise ValidationError("El NF del vuelo no puede ser mayor de 4.")

    def _is_multiple_of_six_minutes(self, value):
        return round(value * 60) % 6 == 0

    def action_cambiar_pantalla_prevuelo(self):
        self.write({'estado_vista': 'prevuelo'})

    def action_cambiar_pantalla_fin_prevuelo(self):
        self.write({'estado_vista': 'fin_prevuelo'})

    def action_cambiar_pantalla_postvuelo(self):
        self.write({'estado_vista': 'postvuelo'})

    def action_cambiar_pantalla_cerrado(self):
        self.write({'estado_vista': 'cerrado'})
    
    def action_cambiar_pantalla_cancelado(self):
        self.write({'estado_vista': 'cancelado'})

    def action_resumen_parte_de_vuelo(self):
        action = self.env.ref('leulit_operaciones.leulit_20240313_1513_action').read()[0]
        action['context'] = {'form_view_initial_mode': 'readonly'}
        action['res_id'] = self.id 
        return action

    def get_data_to_report_27format(self):
        docref = datetime.now().strftime("%Y%m%d")
        hashcode_interno = utilitylib.getHashOfData(docref)
        data = {
            'piloto' : self.piloto_id.name,
            'helicoptero' : self.helicoptero_id.name,
            'fecha' : self.fechavuelo,
            'firma' : self.piloto_id.firma,
            'hashcode_interno' : hashcode_interno,
        }
        company_helipistas = self.env['res.company'].search([('name','like','Helipistas')])
        if company_helipistas:
            data['logo_hlp'] = company_helipistas.logo_reports
        else:
            data['logo_hlp'] = False
        return data

    def print_report_27format(self):
        data = self.get_data_to_report_27format()
        return self.env.ref('leulit_operaciones.leulit_20250507_1537_report').report_action([], data=data)


    def pdf_report_F27_print(self, datos):
        for item in self:
            data = item.get_data_to_report_27format()
            data.update({'firmado_por': datos['firmado_por']})
            data.update({'piloto': datos['firmado_por']})
            data.update({'firma': datos['firma']})
            data.update({'hashcode': datos['hashcode']})

            pdf = self.env.ref('leulit_operaciones.leulit_20250507_1537_report')._render_qweb_pdf([], data=data)[0]
            return base64.encodestring(pdf)
