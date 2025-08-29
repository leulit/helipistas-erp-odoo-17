# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from odoo.addons.leulit import utilitylib
from datetime import datetime

_logger = logging.getLogger(__name__)


class PFAccionLastDone(models.Model):
    _name = "leulit.pf_accion_last_done"
    _description = "leulit_pf_accion_last_done"
    _order = 'done_date desc'

    def _calc_fecha_last_done(self, fecha, idpfa):
        pfa = self.env['leulit.pf_accion'].browse(idpfa)
        if pfa.next_done_date:
            diasdiff = utilitylib.cal_days_diff(pfa.next_done_date, fecha)

            r = range(0, pfa.margen_dy)
            if diasdiff in r:
                if pfa.next_done_date:
                    return pfa.next_done_date
                else:
                    return fecha
            else:
                return fecha
        else:
            return fecha

    def do_done_course(self):
        DATE_FORMAT = utilitylib.STD_DATE_FORMAT
        for item in self:
            fecha = self._calc_fecha_last_done(item.done_date, item.pf_accion.id)
            oldids = self.search([('pf_accion', '=', item.pf_accion.id)])
            oldids.write({'is_last': False})
            self.write({'done_date': item.done_date, 'is_last': True})
            if item.actualizartodos == True:
                acciones = self.env['leulit.pf_accion'].search([('accion','=',item.pf_accion.accion.id),('alumno','=',item.pf_accion.alumno.id),('id','!=',item.pf_accion.id)])
                for accion in acciones:
                    fecha = self._calc_fecha_last_done(item.done_date, accion.id)
                    oldids = self.search([('pf_accion', '=', accion.id)])
                    oldids.write({'is_last': False})
                    if accion.id == item.pf_accion.id:
                        self.write({'done_date': item.done_date, 'is_last': True})
                    else:
                        self.create({'done_date': item.done_date, 'is_last': True, 'pf_accion': accion.id, 'name': item.name})
        return {'type': 'ir.actions.act_window_close'}


    pf_accion = fields.Many2one('leulit.pf_accion', 'Perfil formación acción')
    name = fields.Char("Descripción")
    done_date = fields.Date('Done date')
    is_last = fields.Boolean('¿Es último?')
    documentos_perfil = fields.Many2many('ir.attachment', 'leulit_pf_rel_accion','perfil_rel','doc_rel','Documentos')
    actualizartodos = fields.Boolean(string='',default=True)

