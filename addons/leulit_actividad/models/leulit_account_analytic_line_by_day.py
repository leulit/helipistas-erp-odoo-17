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
from dateutil.relativedelta import relativedelta

from . import actividad_aerea
from . import actividad_laboral

import logging
_logger = logging.getLogger(__name__)


class LeulitAccounAnalyticLineByDay(models.Model):
    _name = "leulit.account.analytic.line.byday"
    _description = "Actividad diaria"
   
    @api.depends('account_analytic_lines','account_analytic_lines.write_date','write_date')
    def _compute_horas_facturables(self):
        for item in self:
            item.horas_facturables =  8.0 if item.horas_imputadas > 8 else item.horas_imputadas
            if item.ruta:
                # temporada alta (Mayo, Junio, Julio, Agosto y septiembre)
                if 5 <= item.fecha.month <= 9:
                    item.horas_facturables =  11.0 if item.horas_imputadas > 11 else item.horas_imputadas
                # temporada baja (el resto de meses)
                else:
                    item.horas_facturables =  8.0 if item.horas_imputadas > 8 else item.horas_imputadas
            if item.guardia:
                item.horas_facturables =  11.0 if item.horas_imputadas > 11 else item.horas_imputadas

    @api.depends('account_analytic_lines','account_analytic_lines.write_date','write_date')
    def _compute_total_horas_imputadas(self):
        for item in self:
            dominio = [('employee_id', '=', item.employee_id.id), ('date', '=', item.fecha)]
            # _logger.error("-_compute_total_horas_imputadas-> dominio %r ",dominio)
            total = 0
            for item1 in self.env['account.analytic.line'].search(dominio):
                total +=  item1.unit_amount
            # _logger.error("-_compute_total_horas_imputadas-> total %r ",total)
            item.total_horas_imputadas = total

    @api.depends('account_analytic_lines','account_analytic_lines.write_date','write_date')
    def _compute_horas_imputadas(self):        
        for item1 in self:   
            employee_id = 0
            dominio = [('employee_id', '=', item1.employee_id.id), ('date', '=', item1.fecha)]
            intervals = []
            for item in self.env['account.analytic.line'].search(dominio):
                employee_id = item.employee_id.id
                fecha = item.date
                if item.date_time and item.date_time_end:
                    inicio = item.date_time.strftime("%H:%M")
                    fin = item.date_time_end.strftime("%H:%M")
                    # _logger.error("--> inicio - fin = %r - %r",inicio,fin)
                    intervals.append( [ self.time_string_to_decimals(inicio), self.time_string_to_decimals(fin) ] )
            # _logger.error("--> employee %r intervals 1 = %r fecha = %r",employee_id, intervals, fecha)
            if len(intervals) > 1:
                intervals.sort(key=lambda x:x[0])
                intervals = utilitylib.merge_intervals(intervals)
            # _logger.error("--> employee %r intervals 2 = %r fecha = %r",employee_id, intervals, fecha)
            total = 0
            if intervals:
                for item in intervals:
                    total += item[1] - item[0]
            # _logger.error("--> employee %r total = %r",employee_id, total)
            item1.horas_imputadas  = total

    @api.depends('account_analytic_lines')
    def _get_ruta_line(self):
        for item in self:
            item.ruta = False
            for line in item.account_analytic_lines:
                if line.ruta:
                    item.ruta = True

    @api.depends('account_analytic_lines')
    def _get_guardia_line(self):
        for item in self:
            item.guardia = False
            for line in item.account_analytic_lines:
                if line.guardia:
                    item.guardia = True

    def time_string_to_decimals(self, time_string):
        fields = time_string.split(":")
        hours = fields[0] if len(fields) > 0 else 0.0
        minutes = fields[1] if len(fields) > 1 else 0.0
        seconds = fields[2] if len(fields) > 2 else 0.0
        return float(hours) + (float(minutes) / 60.0) + (float(seconds) / pow(60.0, 2))

    
    employee_id = fields.Many2one(comodel_name='hr.employee',string='Empleado',ondelete='restrict', index=True)
    user_id = fields.Many2one(related='employee_id.user_id',comodel_name='res.users',string='Usuario')
    account_analytic_lines = fields.One2many('account.analytic.line', 'byday_id', 'Lineas imputación')
    fecha = fields.Date(string="Fecha", index=True)
    dummy = fields.Boolean(string="Dummy")
    total_horas_imputadas = fields.Float(string="Total horas imputadas", compute=_compute_total_horas_imputadas,  digits=(16, 2), compute_sudo=True, store=True)
    horas_imputadas = fields.Float(string="Horas imputadas", compute=_compute_horas_imputadas,  digits=(16, 2), compute_sudo=True, store=True)
    horas_facturables = fields.Float(string="Horas facturables", compute=_compute_horas_facturables,  digits=(16, 2), compute_sudo=True, store=True)
    ruta = fields.Boolean(compute=_get_ruta_line, string='Ruta', compute_sudo=True, store=True)
    guardia = fields.Boolean(compute=_get_guardia_line, string='Guardia', compute_sudo=True, store=True)


    def upd_compute_fields(self):
        _logger.error("upd_compute_fields ")        
        model = self.env["leulit.account.analytic.line.byday"]
        ids = [x.get('id') for x in model.search_read([], ['id'])]
        self.env.all.tocompute[model._fields['ruta']].update(ids)
        self.env.all.tocompute[model._fields['guardia']].update(ids)
        self.env.all.tocompute[model._fields['total_horas_imputadas']].update(ids)
        self.env.all.tocompute[model._fields['horas_imputadas']].update(ids)
        self.env.all.tocompute[model._fields['horas_facturables']].update(ids)
        model.recompute()
        _logger.error("upd_compute_fields end thread")
        return {}

    def set_in_byday_acc_an_line(self):
        _logger.error("################### actualizar datos actividad laboral ")
        threaded_calculation = threading.Thread(target=self.run_set_in_byday_acc_an_line, args=([]))
        _logger.error("################### actualizar datos actividad laboral start thread")
        threaded_calculation.start()

    def run_set_in_byday_acc_an_line(self):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            
            if datetime.now().day <= 10:
                fecha = (datetime.now() - relativedelta(months=1)).date()
            else:
                fecha = datetime.strptime("{0}-{1}-01".format(datetime.now().year,datetime.now().month),"%Y-%m-%d").date()
            project_maintenance_id = int(env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))

            for aaline in env['account.analytic.line'].sudo().search([('project_id','!=',project_maintenance_id),('date','>=',fecha),('vuelo_no_hlp','=',False)]):
                if aaline.employee_id and aaline.date:
                    aaline_byday = env['leulit.account.analytic.line.byday'].sudo().search([('employee_id','=',aaline.employee_id.id),('fecha','=',aaline.date)])
                    if not aaline_byday:
                        aaline_byday_new = env['leulit.account.analytic.line.byday'].sudo().create({'employee_id':aaline.employee_id.id,'fecha':aaline.date})
                        aaline.write({'byday_id':aaline_byday_new.id})
                    else:
                        aaline.write({'byday_id':aaline_byday.id})
                    new_cr.commit()
            
            model = env["leulit.account.analytic.line.byday"]
            ids = [x.get('id') for x in model.search_read([], ['id'])]
            env.all.tocompute[model._fields['total_horas_imputadas']].update(ids)
            env.all.tocompute[model._fields['horas_imputadas']].update(ids)
            env.all.tocompute[model._fields['horas_facturables']].update(ids)
            model.recompute()
        _logger.error('################### actualizar datos actividad laboral fin thread')

    

    def set_in_byday_acc_an_line_with_fecha(self, fecha):
        _logger.error("################### actualizar datos actividad laboral ")
        threaded_calculation = threading.Thread(target=self.run_set_in_byday_acc_an_line_with_fecha, args=([fecha]))
        _logger.error("################### actualizar datos actividad laboral start thread")
        threaded_calculation.start()

    def run_set_in_byday_acc_an_line_with_fecha(self, fecha='2025-01-01'):
        db_registry = registry(self.env.cr.dbname)
        with db_registry.cursor() as new_cr:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            
            project_maintenance_id = int(env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))
            for aaline in env['account.analytic.line'].sudo().search([('project_id','!=',project_maintenance_id),('date','>=',fecha),('vuelo_no_hlp','=',False)], order="date ASC"):
                _logger.error('################### account_analytic_line --> %r',aaline)
                _logger.error('################### account_analytic_line --> %r',aaline.date)
                if aaline.employee_id and aaline.date:
                    aaline_byday = env['leulit.account.analytic.line.byday'].sudo().search([('employee_id','=',aaline.employee_id.id),('fecha','=',aaline.date)])
                    if not aaline_byday:
                        aaline_byday_new = env['leulit.account.analytic.line.byday'].sudo().create({'employee_id':aaline.employee_id.id,'fecha':aaline.date})
                        aaline.write({'byday_id':aaline_byday_new.id})
                    else:
                        aaline.write({'byday_id':aaline_byday.id})
                    new_cr.commit()
            
            model = env["leulit.account.analytic.line.byday"]
            ids = [x.get('id') for x in model.search_read([], ['id'])]
            env.all.tocompute[model._fields['total_horas_imputadas']].update(ids)
            env.all.tocompute[model._fields['horas_imputadas']].update(ids)
            env.all.tocompute[model._fields['horas_facturables']].update(ids)
            model.recompute()
        _logger.error('################### actualizar datos actividad laboral fin thread')
