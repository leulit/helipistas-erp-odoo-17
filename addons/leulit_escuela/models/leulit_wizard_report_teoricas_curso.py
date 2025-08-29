# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)

class leulit_wizard_report_teoricas_curso(models.TransientModel):
    _name = "leulit.wizard_report_teoricas_curso"
    _description = "leulit_wizard_report_teoricas_curso"

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
        asignatura_instance = self.env['leulit.asignatura']
        alumno_instance = self.env['leulit.alumno']
        curso_instance = self.env['leulit.curso']
        cursos_data = []
        for curso in self.cursos:
            partesdb = parte_escuela_instance.search([('cursos','in',[curso.curso_id.id]),('alumnos','=',self.alumno.id),('vuelo_id','=',False),('estado','=','cerrado')])
            partes = []
            for parte in partesdb:
                strsilabus = ""
                verificado = True
                for item in parte.rel_curso_alumno:
                    if self.alumno.id == item.alumno.id:
                        if not item.verificado:
                            verificado = False
                        if item.rel_silabus.name:                  
                            strsilabus = strsilabus + item.rel_silabus.name + "<br/>"
                partes.append({
                    'id': parte.id,
                    'fecha': parte.fecha,
                    'horainicio': utilitylib.leulit_float_time_to_str(parte.hora_start),
                    'tiempo': utilitylib.leulit_float_time_to_str(parte.tiempo),
                    'silabus': strsilabus,
                    'comentario': parte.comentario,
                    'valoracion': parte.valoracion,
                    'firmainstructor': '<img %s  src="data:image/%s;base64,%s" />' % ("height='25px'", "jpg", str(parte.profesor.firma)),
                    'instructor': parte.profesor.name,
                    'firmaalumno': '<img %s  src="data:image/%s;base64,%s" />' % ("height='25px'", "jpg", str(self.alumno.firma)) if verificado else '',
                    'nombrealumno': self.alumno.name,
                })
            asignaturas = []
            for asignatura in curso.curso_id.asignatura_ids:
                asignaturas.append({
                    'name': asignatura.descripcion,
                    'horasprevistas': asignatura_instance.get_horasTeoricas_byCurso(asignatura.id,curso.curso_id.id),
                    'horasrecibidas': alumno_instance._get_horas_by_tipo_curso_asignatura(self.alumno.id,curso.curso_id.id,asignatura.id, 'teorica')
                })
            cursos_data.append({
                'curso': curso.curso_id.name,
                'horasprevistas': curso.curso_id.total_horas_teorico,
                'horasrecibidas': utilitylib.leulit_float_time_to_str(curso_instance._get_horas_by_tipo_alumno_curso(self.alumno.id,curso.curso_id.id, 'teorica')),
                'asignaturas': asignaturas,
                'partes': partes
            })
        datos['alumno_nombre'] = self.alumno.name
        datos['datos'] = cursos_data      
        
        if firmar:
            datos['date_hashcode'] = utilitylib.getStrTodayFullIsoFormat()
            hashdatos = utilitylib.getHashOfData(datos)
            hashcode = "ESC_ALU_PR-{0}".format(hashdatos)
            datos['hashcode'] = hashcode
            datos['firmado_por'] = self.env.user.name
            datos['firmado'] = True
        else:
            datos['hashcode'] = None
            datos['firmado_por'] = None 
            datos['firmado'] = False
        
        return datos

    def create_report(self, datos):        
        return self.env.ref('leulit_escuela.wizard_report_teoricas_curso_report').report_action(self,data=datos)
    
    alumno = fields.Many2one(comodel_name='leulit.alumno', string='Alumno')
    cursos = fields.Many2many('leulit.rel_alumno_curso', relation='leulit_relation_002', column1='popup_rel', column2='curso_id', string='Cursos')
    
