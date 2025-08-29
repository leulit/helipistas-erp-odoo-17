# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)



class leulit_report_curso_pf(models.AbstractModel):
    _name = 'leulit.report_curso_pf'
    _descripcion = 'leulit.report_curso_pf'
    _auto = False


    def getDataPdf(self, cursospf, alumno, nameperfil):
        context = {}
        parte_escuela_instance = self.env['leulit.parte_escuela']
        rpeca_instance = self.env['leulit.rel_parte_escuela_cursos_alumnos']
        vuelo_instance = self.env['leulit.vuelo']
        pg_silabus = self.env['leulit.silabus']
        datos = []
        verificado = 0
        calculotiempo = {}

        for cursopf in cursospf:
            #cursos = self.pool.get('helipistas.curso').read(cr, uid, cursopf['curso'], ['silabus_teorico_ids', 'silabus_practico_ids', 'id', 'name'], context)
            cursos = cursopf['curso']
            fecha_ini = cursopf['fecha_ini']
            fecha_fin = cursopf['fecha_fin']
            valido_desde = cursopf['valido_desde']
            valido_hasta = cursopf['valido_hasta']
            for curso in [cursos]:
                silabus_teoria = curso.silabus_teorico_ids
                silabus_practica = curso.silabus_practico_ids
                objdatos = {
                    'id': curso.id,
                    'name': curso.name,
                    'silabus_teoria': [],
                    'silabus_practica': [],
                    'tiempo' : "00:00",
                    'valido_desde': valido_desde,
                    'valido_hasta': valido_hasta
                }
                calculotiempo = {}
                for silabus in silabus_teoria:
                    items_rpeca = rpeca_instance.get_partes_alumno_by_curso_and_silabus_fechas(alumno.id, curso.id, silabus.id, fecha_ini, fecha_fin)
                    if items_rpeca:
                        items_rpeca = rpeca_instance.browse(items_rpeca)
                        if len(items_rpeca) > 0:
                            for item_rpeca in items_rpeca:
                                objsilabus = {
                                    'fecha': '',
                                    'name': silabus.name,
                                    'comentario': silabus.comentario,
                                    'id': silabus.id,
                                    'firmaprofe': '',
                                    'nombreprofe': '',
                                    'valoracion': '',
                                    'verificado': '',
                                    'comentario_parte': '',
                                    'id_parte': '',
                                    'estado_parte': '',
                                    'valoracion_parte':'',
                                }
                                objparte = parte_escuela_instance.browse(item_rpeca.rel_parte_escuela.id)
                                objsilabus['fecha'] = item_rpeca.fecha
                                if not objparte.id in calculotiempo:
                                    calculotiempo[objparte.id] = objparte.tiempo
                                objsilabus['nombreprofe'] = item_rpeca.profesor_id.name
                                objsilabus['firmaprofe'] = '<img %s  src="data:image/%s;base64,%s" />' % ("height='25px'", "jpg", str(item_rpeca.profesor_id.firma))
                                objsilabus['verificado'] = item_rpeca.verificado
                                objsilabus['valoracion'] = item_rpeca.valoracion
                                objsilabus['comentario_parte'] = objparte.comentario
                                objsilabus['estado_parte'] = objparte.estado
                                objsilabus['id_parte'] = objparte.id
                                objsilabus['valoracion_parte'] = objparte.valoracion
                                objdatos['silabus_teoria'].append(objsilabus)
                    else:
                        objsilabus = {
                            'fecha': '',
                            'name': silabus.name,
                            'comentario': silabus.comentario,
                            'id': silabus.id,
                            'firmaprofe': '',
                            'nombreprofe': '',
                            'valoracion': '',
                            'verificado': '',
                            'comentario_parte': '',
                            'id_parte': '',
                            'estado_parte': '',
                            'valoracion_parte':'',
                        }
                        objdatos['silabus_teoria'].append(objsilabus)

                
                tiempo = 0
                for key in calculotiempo:
                    tiempo = tiempo + calculotiempo[key]
                objdatos['tiempo'] = utilitylib.leulit_float_time_to_str(tiempo)

                for silabus in silabus_practica:
                    items_rpeca = rpeca_instance.get_partes_alumno_by_curso_and_silabus_fechas(alumno.id, curso.id, silabus.id, fecha_ini, fecha_fin)
                    if items_rpeca:
                        items_rpeca = rpeca_instance.browse(items_rpeca)
                        if len(items_rpeca) > 0:
                             partes_rpeca = []
                             for item_rpeca in items_rpeca:
                                objsilabus = {
                                    'fecha': '',
                                    'name': silabus.name,
                                    'comentario': silabus.comentario,
                                    'id': silabus.id,
                                    'firmaprofe': '',
                                    'nombreprofe': '',
                                    'maquina': '',
                                    'piloto': '',
                                    'hora_salida': '',
                                    'hora_llegada': '',
                                    'valoracion': '',
                                    'comentario_parte': '',
                                    'id_parte': '',
                                    'estado_parte': '',
                                    'verificado': '',
                                    'valoracion_parte':'',
                                }
                                items_rpeca = items_rpeca[0]
                                objparte = parte_escuela_instance.browse(item_rpeca.rel_parte_escuela.id)
                                objsilabus['fecha'] = objparte.fecha
                                objsilabus['firmaprofe'] = '<img %s  src="data:image/%s;base64,%s" />' % ("height='25px'", "jpg", str(item_rpeca.profesor_id.firma))
                                objsilabus['nombreprofe'] = item_rpeca.profesor_id.name
                                if objparte.vuelo_id:
                                    objsilabus['maquina'] = objparte.vuelo_id.helicoptero_id.name
                                    objsilabus['hora_salida'] = objparte.vuelo_id.strhorasalida
                                    objsilabus['hora_llegada'] = objparte.vuelo_id.strhorallegada
                                    if objparte.vuelo_id.piloto_supervisor_id:
                                        objsilabus['piloto'] = objparte.vuelo_id.piloto_supervisor_id.name
                                    else:
                                        if objparte.vuelo_id.piloto_id:
                                            objsilabus['piloto'] = objparte.vuelo_id.piloto_id.name
                                else:
                                    objsilabus['maquina'] = ""
                                    objsilabus['hora_salida'] = ""
                                    objsilabus['hora_llegada'] = ""

                                objsilabus['verificado'] = item_rpeca.verificado
                                objsilabus['valoracion'] = item_rpeca.valoracion
                                objsilabus['comentario_parte'] = objparte.comentario
                                objsilabus['id_parte'] = objparte.id
                                objsilabus['estado_parte'] = objparte.estado
                                objsilabus['valoracion_parte'] = objparte.valoracion
                            
                                objdatos['silabus_practica'].append(objsilabus)
                    else:
                        objsilabus = {
                                    'fecha': '',
                                    'name': silabus.name,
                                    'comentario': silabus.comentario,
                                    'id': silabus.id,
                                    'firmaprofe': '',
                                    'nombreprofe': '',
                                    'maquina': '',
                                    'piloto': '',
                                    'hora_salida': '',
                                    'hora_llegada': '',
                                    'valoracion': '',
                                    'comentario_parte': '',
                                    'id_parte': '',
                                    'estado_parte': '',
                                    'verificado': '',
                                    'valoracion_parte':'',
                                }
                        objdatos['silabus_practica'].append(objsilabus)

            datos.append(objdatos)
        data = {}
        data['alumno_nombre'] = alumno.name
        if verificado == 0:
            data['alumno_firma'] = '<img %s  src="data:image/%s;base64,%s" />' % ("height='25px'", "png", str(alumno.firma))
            data['alumno_firma'] = ""
        else:
            data['alumno_firma'] = "Parte por verificar: %r" % verificado
        
        company_helipistas = self.env['res.company'].search([('name','like','Helipistas')])
        data['logo_hlp'] = company_helipistas.logo_reports if company_helipistas else False
        data['datos'] = datos
        return data