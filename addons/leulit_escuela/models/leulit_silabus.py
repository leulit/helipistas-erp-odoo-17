from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger     = logging.getLogger(__name__)


class leulit_silabus(models.Model):
    _name           = "leulit.silabus"
    _description    = "leulit_silabus"
    _order          = "asignatura_id  asc, orden asc"


    @api.model
    def create(self,vals):
        if 'curso_id' in vals:
            last_silabus = self.search([('curso_id','=',vals['curso_id'])],order="orden desc",limit=1)
            for last in last_silabus:
                vals['orden'] = last.orden+1
        result = super(leulit_silabus, self).create(vals)
        return result

    
    def act_curs_done(self, piloto, fechavuelo, cursos, id_parte):
        #BUCLE PARA ENCONTRAR TODOS LOS CURSOS DEL VUELO EN PARTES ESCUELA Y SUMAR EL TIEMPO
        fecha = fechavuelo
        for curso in self.env['leulit.curso'].browse(cursos):
            # HACER UN BUCLE PARA CALCULAR EL DONE POR PERFIL
            # PRIMERO OBTENEMOS LOS PERFILES DE FORMACIÓN DEL PILOTO
            fecha_pf = datetime.strptime('2000-01-01', '%Y-%m-%d').date()
            id_pf_curso = self.env['leulit.perfil_formacion_curso'].search([('is_template','=',False),('alumno','in', [piloto]),('curso','=',curso.id)])
            silabus_in_cursos = []
            for perfil_curso in id_pf_curso:
                if perfil_curso.last_done_date:
                    if fecha_pf < perfil_curso.last_done_date:
                        fecha_pf = perfil_curso.last_done_date

            # LEEMOS TODOS LOS PARTES
            partes = self.env['leulit.parte_escuela'].search([('cursos', 'in', [curso.id]),('alumnos', 'in', [piloto]),('fecha', '>=', fecha_pf)])
            silabus_in_partes = []
            for parte in partes:
                for silabus in parte.silabus:
                    if silabus.id in curso.silabus_ids.ids:
                        if silabus.id not in silabus_in_partes:
                            silabus_in_partes.append(silabus.id)

            if len(silabus_in_partes) == len(curso.silabus_ids):
                for pf_curso in id_pf_curso:
                    self.env['leulit.perfil_formacion_curso_last_done'].mark_pfc_done(pf_curso.id, fechavuelo)


    name = fields.Char('Descripción', required=True)
    comentario = fields.Html('Comentario')
    orden = fields.Integer('Orden')
    duracion = fields.Float('Duración (hh:mm)')
    curso_id = fields.Many2one('leulit.curso','Curso')
    rel_alumno_curso_ids = fields.Many2one('leulit.rel_alumno_curso','Rel alumno curso')
    tipo = fields.Selection([('teorica', 'Teórica'),('practica', 'Práctica')], 'Tipo')
    sesion = fields.Selection([('nodef', 'No definida'),('VBD', 'VBD'),('VBDS', 'VBDS'),('TV', 'TV'),('VTD', 'VTD'),('VTS', 'VTS'),('VBS', 'VBS'),('IBD', 'IBD'),('NBD', 'NBD'),('NBS', 'NBS'),('FAM', 'FAM')], 'Sesion')
    asignatura_id = fields.Many2one('leulit.asignatura','Asignatura')
    silabusDoit = fields.Boolean('Silabus Doit')
    vts = fields.Boolean('VTS/VBS/NBS')
    spic = fields.Boolean('TV/VBDS')
    doblemando = fields.Boolean('VBD/VTD/IBD/NBD')
    test = fields.Boolean('TEST')
    valoracion = fields.Boolean('Valoración')
    night = fields.Boolean('Nocturno')