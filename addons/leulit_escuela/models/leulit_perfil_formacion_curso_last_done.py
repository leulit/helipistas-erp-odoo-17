# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
import threading
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_perfil_formacion_curso_last_done(models.Model):
    _name = "leulit.perfil_formacion_curso_last_done"
    _description = "leulit_perfil_formacion_curso_last_done"
    _order = 'done_date desc'


    def _calc_fecha_last_done(self, fecha, idpf):
        """
            Función para calcular la fecha de realización del cursos
            :param fechavuelo: Fecha en que el usuario ha indicado que se ha realizado el último parte, verificación, examen, etc.. que cierra el curso
            :param idpf: Id del perfil de formación sobre el que estamos actuando

            El cálculo sigue los siguientes criterios:

                a) Si la fecha indicada es anterior, no superior a 3 meses, a la fecha de finalización se marca como fecha de realización la fecha prevista de finalización.
                b) Si la fecha indicada es anterior, superior a 3 meses, a la fecha de finalización se marca como fecha de realización la fecha pasada como parámetro
                c) Si la fecha es posterior a la fecha de finalización idem caso ( b )
        """
        # Obtenemos el curso del pérfil de formación para acceder la fecha de finalización (next_done_date)
        pfc = self.env['leulit.perfil_formacion_curso'].browse(idpf)


        if pfc.next_done_date:
            # Cálculamos la diferencia de días entre ambas fechas
            diasdiff = utilitylib.cal_days_diff(pfc.next_done_date, fecha)

            r = range(0, pfc.marge_dy+1)
            if diasdiff in r:
                if pfc.next_done_date:
                    return pfc.next_done_date
                else:
                    return fecha
            else:
                return fecha
        else:
            return fecha


    def do_done_course(self):
        for item in self:
            fecha = self._calc_fecha_last_done(item.done_date, item.pf_curso.id)
            oldids = self.search([('pf_curso', '=', item.pf_curso.id)])
            oldids.write({'is_last': False})
            item.write({'done_date': fecha, 'is_last': True})
            if item.actualizarTodos == True:
                cursos = self.env['leulit.perfil_formacion_curso'].search([('curso', '=', item.pf_curso.curso.id), ('alumno', '=', item.pf_curso.alumno.id),('id','!=',item.pf_curso.id)])
                for cursoID in cursos:
                    fecha = self._calc_fecha_last_done(item.done_date, cursoID.id)
                    oldids = self.search([('pf_curso', '=', cursoID.id)])
                    oldids.write({'is_last': False})
                    if cursoID == item.pf_curso.id:
                        item.write({'done_date': fecha, 'is_last': True})
                    else:
                        item = self.create({'done_date': fecha, 'is_last': True, 'pf_curso': cursoID.id, 'name': item.name})
        return {'type': 'ir.actions.act_window_close'}
    

    def mark_pfc_done(self, idpf, fechavuelo):
        fecha = self._calc_fecha_last_done(fechavuelo, idpf)
        # Marcar como antiguos (is_last = false) los anteriores registros de curso realizados
        # Obtenemos los ids de registros de realización referente a la tarea
        oldids = self.search([('pf_curso', '=', idpf)])
        # marcamos los registros como antiguos
        for oldid in oldids:
            oldid.is_last = False
    
        valores = {
            'pf_curso': idpf,
            'name': '',
            'done_date': fecha,
            'is_last': True,
        }
        self.create( valores )
   

    def getdata_informe_general_cursos_alu_ld(self):    
        for item in self:
            fecha_ini = False
            fecha_fin = False
            nitems = len(item.pf_curso.last_done_history)
            for i in range(0, nitems):
                itempfc = item.pf_curso.last_done_history[i]
                if itempfc.id == item.id:
                    fecha_fin = itempfc.done_date
                    if i < nitems - 1:
                        fecha_ini = item.pf_curso.last_done_history[i + 1].done_date
                    break            
            valido_hasta = item.pf_curso._calculateNextDoneDate(item.pf_curso.periodicidad_dy,fecha_fin)
            cursospf = []
            nameperfil = ''
            cursospf.append({
                'fecha_ini': fecha_ini,
                'fecha_fin': fecha_fin,
                'curso': item.pf_curso.curso,
                'valido_desde': fecha_fin,
                'valido_hasta': valido_hasta,
            })
            data = self.env['leulit.report_curso_pf'].getDataPdf(cursospf, item.pf_curso.alumno, nameperfil)
            return data
            

    def informe_general_cursos_alu_ld(self):    
            data = self.getdata_informe_general_cursos_alu_ld()
            return self.env.ref('leulit_escuela.report_curso_pf').report_action(self,data=data)


    @api.depends('pf_curso','done_date')
    def _last_parte(self):
        for item in self:
            pfcurso = item.pf_curso
            last_fecha = False
            last_id = False
            if not pfcurso.alumno:
                alumno_id = pfcurso.perfil_formacion.alumno.id
            else:
                alumno_id = pfcurso.alumno.id
            parte_search = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('alumno', '=', alumno_id),('rel_curso', '=', pfcurso.curso.id),('fechaparte','<=',item.done_date)])
            for item2 in parte_search:
                parte = item2.rel_parte_escuela
                if parte.estado == 'cerrado' and parte.fecha <= item.done_date:
                    if not last_fecha or parte.fecha > last_fecha:
                        last_fecha = parte.fecha
                        last_id = parte.id
            item.last_parte = last_fecha
            item.last_parte_id = last_id


    def unlink(self):
        for item in self:
            if hasattr(item, 'is_last'):
                if item.is_last == True:
                    id_pf_curso = item.pf_curso.id
                    pf_curso = self.env['leulit.perfil_formacion_curso'].browse(id_pf_curso)
                    id = ''
                    fecha = None
                    for item2 in pf_curso.last_done_history:
                        if item2.id != item.id:
                            if not fecha or fecha < item2.done_date:
                                fecha = item2.done_date
                                id = item2.id
                    self.env['leulit.perfil_formacion_curso_last_done'].browse(id).write({'is_last': True})
                    
                super(leulit_perfil_formacion_curso_last_done, self).unlink()
                ##-->DEBERÍA UTILIZARSE STORE TRUE I DEPENDS --> self.pool['leulit.perfil_formacion_curso'].updSemaforosCurso(id_pf_curso)


    @api.onchange('done_date')
    def onchange_done_date(self):
        for item in self:
            ##    OBJETOS NECESARIOS
            object_pf_curso = self.env['leulit.perfil_formacion_curso']
            ## BÚSCAMS LAST DONE DATE DEL CURSO
            curso_pf = object_pf_curso.browse(item.pf_curso.id)
            last_date = curso_pf.last_done_date
            ## SI LA FECHA ÉS MAS GRANDE QUE LAST DONE DATE
            if not last_date:
                ok_value = True
            else:
                if item.done_date > last_date:
                    ok_value = True
                else:
                    ok_value = False
            ## MOSTRAMOS EL BOTÓN GUARDAR O MOSTRAMOS ERROR DE FECHA
            item.save_curso_last_done = ok_value
            if not ok_value:
                raise UserError(_(u'La fecha seleccionada no és correcta'))


    pf_curso = fields.Many2one('leulit.perfil_formacion_curso', 'Perfil formacion curso')
    name = fields.Char("Descripcion")
    done_date = fields.Date('Done date')
    is_last = fields.Boolean('¿Es último?')
    actualizarTodos = fields.Boolean(string='',default=True)
    documentos_perfil = fields.Many2many('ir.attachment', 'leulit_perfil_rel_curso', 'perfil_rel', 'doc_rel','Documentos')
    save_curso_last_done = fields.Boolean('¿Se ha de guardar?')
    piloto = fields.Many2one(related='pf_curso.piloto',comodel_name='leulit.piloto',string='Piloto')
    alumno = fields.Many2one(related='pf_curso.alumno',comodel_name='leulit.alumno',string='Alumno')
    last_parte = fields.Char(compute=_last_parte,string='Last parte',store=False)
    last_parte_id = fields.Char(compute=_last_parte,string='Last parte id',store=False)




