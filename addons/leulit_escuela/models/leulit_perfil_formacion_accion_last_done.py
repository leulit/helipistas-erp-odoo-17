# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib
from datetime import datetime

_logger = logging.getLogger(__name__)


class leulit_perfil_formacion_accion_last_done(models.Model):
    _name = "leulit.perfil_formacion_accion_last_done"
    _description = "leulit_perfil_formacion_accion_last_done"
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
        pfc = self.env['leulit.perfil_formacion_accion'].browse(idpf)


        if pfc.next_done_date:
            # Cálculamos la diferencia de días entre ambas fechas
            diasdiff = utilitylib.cal_days_diff(pfc.next_done_date, fecha)

            r = range(0, 90)
            if diasdiff in r:
                if pfc.next_done_date:
                    return pfc.next_done_date
                else:
                    return fecha
            else:
                return fecha
        else:
            return fecha

        

    # def mark_pfc_done(self, cr, uid, idpf, fechavuelo):
    #     fecha = self._calc_fecha_last_done(cr, uid, fechavuelo, idpf)

    #     # Marcar como antiguos (is_last = false) los anteriores registros de curso realizados
    #     # obtenemos los ids de registros de realización referente a la tarea
    #     oldids = self.search(cr, uid, [('pf_accion', '=', idpf)])
    #     # marcamos los registros como antiguos
    #     self.write(cr, uid, oldids, {'is_last': False})

    #     valores = {
    #         'pf_accion': idpf,
    #         'name': '',
    #         'done_date': fecha,
    #         'is_last': True,
    #     }
    #     self.create(cr, uid, valores, None)

    


    # def informe_general_cursos_alu(self, cr, uid, ids, context=None):
    #     for item in self.browse(cr, uid, ids, context):
    #         pilotoid = item.pf_accion.perfil_formacion.piloto.id
    #         alumnoid = self.env['leulit.alumno').search(cr, uid, [('piloto_id', '=', pilotoid)])
    #         alumno = self.env['leulit.alumno').browse(cr, uid, alumnoid, ['nombre','apellidos','firma_user'],context)[0]
    #         cursoid = self.env['leulit.curso').search(cr, uid, [('id','=',item.pf_accion.curso.id)])

    #         #TODO:---

    #         return self.env['leulit.wizard_report_curso').buildpdf_wrc(cr, uid, cursoid, pilotoid, alumno['nombre'], alumno['apellidos'], alumno['firma_user'], '', context)


    # def unlink(self, cr, uid, ids, context=None):
    #     for item in self.browse(cr,uid,ids,context):
    #         if hasattr(item, 'is_last'):
    #             if item.is_last == True:
    #                 id_pf_accion = item.pf_accion.id
    #                 pf_accion = self.env['leulit.perfil_formacion_accion').browse(cr,uid,id_pf_accion)
    #                 id=''
    #                 fecha=''
    #                 for item2 in pf_accion.last_done_history:
    #                     if item2.id != ids[0]:
    #                         if fecha < item2.done_date:
    #                             fecha = item2.done_date
    #                             id = item2.id
    #                 self.env['leulit.perfil_formacion_accion_last_done').write(cr, uid, id, {'is_last' : True })
    #                 super(leulit_perfil_formacion_accion_last_done, self).unlink(cr, uid, item.id, context=context)        
    #             else:
    #                 super(leulit_perfil_formacion_accion_last_done, self).unlink(cr, uid, item.id, context=context)

    def do_done_course(self):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        for item in self:
            if item.actualizartodos == True:
                acciones = self.env['leulit.perfil_formacion_accion'].search([('descripcion','=',item.pf_accion.descripcion),('piloto','=',item.pf_accion.piloto.id)])
                for accion in acciones:
                    oldids = self.search([('pf_accion', '=', accion.id)])
                    oldids.write({'is_last': False})
                    if accion.id == item.pf_accion.id:
                        self.write({'done_date': item.done_date, 'is_last': True})
                    else:
                        self.create({'done_date': item.done_date, 'is_last': True, 'pf_accion': accion.id, 'name': item.name})
                
            else:
                oldids = self.search([('pf_accion', '=', item.pf_accion.id)])
                oldids.write({'is_last': False})
                self.write({'done_date': item.done_date, 'is_last': True})
        return True


    pf_accion = fields.Many2one('leulit.perfil_formacion_accion', 'Perfil formacion accion')
    name = fields.Char("Descripcion")
    done_date = fields.Date('Done date')
    is_last = fields.Boolean('¿Es último?')
    documentos_perfil = fields.Many2many('ir.attachment', 'leulit_perfil_rel_accion','perfil_rel','doc_rel','Documentos')
    actualizartodos = fields.Boolean('')

