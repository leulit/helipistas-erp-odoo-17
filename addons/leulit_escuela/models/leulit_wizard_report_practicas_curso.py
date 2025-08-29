# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)



class leulit_wizard_report_practicas_curso(models.TransientModel):
    _name        = "leulit.wizard_report_practicas_curso"
    _description = "leulit_wizard_report_practicas_curso"

    def imprimir(self):
        datos = self.build_report(False)
        return self.create_report(datos)        
        
    def build_report(self, firmar):
        if self.cursos:            
            return self.build_report_data(firmar)
        else:
            raise UserError('Falta seleccionar cursos')            
    
    def build_report_data(self,firmar):
        datos = {}
        parte_escuela_instance = self.env['leulit.parte_escuela']
        total_tiempo_servicio = 0
        for item in self:                
            cursos_data = []
            for curso in item.cursos:
                partes = parte_escuela_instance.search([('cursos','in',[curso.curso_id.id]),('alumnos','=',item.alumno.id),('vuelo_id','!=',False),('estado','=','cerrado')])
                vuelos = []
                for parte in partes:
                    strsilabus = ""
                    verificado = True
                    for item in parte.rel_curso_alumno:
                        if item.alumno.id == item.alumno.id:
                            if not item.verificado:
                                verificado = False
                            if item.rel_silabus.name:
                                strsilabus = strsilabus + item.rel_silabus.name + "<br/>"
                    vuelos.append({
                        'id': parte.vuelo_id.id,
                        'codigo': parte.vuelo_id.codigo,
                        'fechavuelo': parte.vuelo_id.fechavuelo,
                        'lugarsalida': parte.vuelo_id.lugarsalida.name,
                        'strhorasalida': utilitylib.leulit_float_time_to_str(parte.vuelo_id.horasalida),
                        'lugarllegada': parte.vuelo_id.lugarllegada.name,
                        'strhorallegada': utilitylib.leulit_float_time_to_str(parte.vuelo_id.horallegada),
                        'piloto': parte.vuelo_id.piloto_id.name,
                        'doblemando': parte.vuelo_id.doblemando,
                        'strtiemposervicio': parte.vuelo_id.strtiemposervicio,
                        'tiemposervicio': parte.vuelo_id.tiemposervicio,
                        'matricula': parte.vuelo_id.helicoptero_id.name,
                        'landings': (parte.vuelo_id.landings + parte.vuelo_id.nightlandings),
                        'silabus': strsilabus,
                        'comentario': parte.comentario,
                        'valoracion': parte.valoracion,
                        'firmainstructor': '<img %s  src="data:image/%s;base64,%s" />' % ("height='25px'", "jpg", str(parte.vuelo_id.piloto_id.firma)),
                        'instructor': parte.vuelo_id.piloto_id.name,
                        'firmaalumno': '<img %s  src="data:image/%s;base64,%s" />' % ("height='25px'", "jpg", str(item.alumno.firma)) if verificado else '',
                        'nombrealumno': item.alumno.name,
                    })
                    total_tiempo_servicio += parte.vuelo_id.tiemposervicio
                
                cursos_data.append({
                    'curso': curso.curso_id.name,
                    'horasprevistas': curso.curso_id.total_horas_practico,
                    'horasrecibidas': utilitylib.leulit_float_time_to_str(total_tiempo_servicio),
                    'vuelos': vuelos
                })

            datos['alumno_nombre'] = item.alumno.name
            datos['datos'] = cursos_data      
        
        if firmar:
            datos['date_hashcode'] = utilitylib.getStrTodayFullIsoFormat()
            hashdatos = utilitylib.getHashOfData(datos)
            hashcode = "ESC_ALU_PR-{0}".format(hashdatos)
            datos['hashcode'] = hashcode
            datos['firmado_por'] = self.env.user.name
            datos['firmado'] = True
        else:
            datos['firmado'] = False
            
        return datos

    def create_report(self, datos):        
        return self.env.ref('leulit_escuela.wizard_report_practicas_curso_report').report_action(self,data=datos)

    alumno = fields.Many2one(comodel_name='leulit.alumno', string='Alumno')
    cursos = fields.Many2many('leulit.rel_alumno_curso', relation='leulit_rel_wizard_alumno_curso', column1='wizard_id', column2='alumno_curso_id', string='Cursos')
    


