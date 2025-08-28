# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
import pytz
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp
import threading
from datetime import datetime, date, timedelta
import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.constrains('date_time','unit_amount','user_id')
    def _check_date_imputacion_horas(self):
        if not self.user_has_groups('leulit_tarea.RT_gestor'):
            for item in self:
                if item.user_id:
                    # No imputar sin haber verificado todas las circulares
                    circulares = self.env['leulit.historial_circular'].search([('user_id', '=', item.user_id.id),('circular_id','!=',False)])
                    for circular in circulares:
                        if not circular.recibido or not circular.leido or not circular.entendido:
                            raise ValidationError("No se puede imputar tiempo sin haber recibido, leído y entendido todas las circulares.")
                    # No imputar sin haber verificado el parte escuela
                    alumno = self.env['leulit.alumno'].search([('partner_id', '=', item.user_id.partner_id.id)])
                    date_now = datetime.now().date()
                    partes_escuela = self.env['leulit.rel_parte_escuela_cursos_alumnos'].search([('verificado', '=', False),('estado','=','cerrado'),('alumno','=',alumno.id),('fecha','<=',date_now)])
                    for parte_escuela in partes_escuela:
                        _logger.error("parte_escuela %s" % parte_escuela.rel_parte_escuela.id)
                        raise ValidationError("No se puede imputar tiempo sin haber verificado los parte de escuela que estás como alumno.")
                    # No imputar sin haber marcado la asistencia a todas las reuniones
                    reuniones = self.env['leulit.reunion_asistente'].search([('user_id', '=', item.user_id.id),('asistencia','=',False)])
                    if len(reuniones) > 0:
                        _logger.error("reuniones %s" % reuniones)
                        raise ValidationError("No se puede imputar tiempo sin haber marcado la asistencia a todas las reuniones.")
                if item.date_time:
                    if item.task_id.date_deadline:
                        if item.date_time.date() > item.task_id.date_deadline:
                            raise ValidationError("No se puede imputar con fecha posterior a la fecha límite.")
                    # No imputar con fecha posterior al dia actual
                    if item.date_time.date() > datetime.now().date():
                        raise ValidationError("No se puede imputar con fecha posterior a hoy.")
                    
                    # No imputar haciendo que las horas lleguen al dia siguiente
                    hora_imputacion = utilitylib.leulit_datetime_to_float_time(item.date_time.astimezone(pytz.timezone("Europe/Madrid")))
                    if item.unit_amount:
                        if hora_imputacion + item.unit_amount >= 24:
                            raise ValidationError("Estás imputando tiempo hasta el día de mañana, imputa menos horas o cambia la hora de inicio.")
                    
                    project_escuela = self.env['project.project'].search([('name','=','HORAS PARTES ESCUELA')])
                    if item.project_id.id != project_escuela.id:
                        # No imputar
                        hace_3_dias = (datetime.now().date()-timedelta(days=3))
                        #######  Formato para la regla de 3 dias antes.
                        if item.date_time.date() < hace_3_dias:
                            raise ValidationError("No puedes imputar tiempo de hace más de 3 días antes.")
                        

    sale_order = fields.Many2one(comodel_name='sale.order', string='Presupuesto', domain=[('flag_flight_part','=',True),('state','=','sale'),('tag_ids','=',False),('task_done','=',False)])
