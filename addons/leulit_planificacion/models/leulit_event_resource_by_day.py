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


class LeulitEventResourceByDay(models.Model):
    _name = "leulit.event.resource.byday"
    _description = "Horas Planificadas"
   

    @api.depends('event_resource_lines','event_resource_lines.write_date','write_date')
    def _compute_total_horas_planificadas(self):
        for item in self:
            dominio = [('resource', '=', item.resource.id), ('date', '=', item.fecha)]
            total = 0
            ids = []
            for item1 in self.env['leulit.event_resource'].search(dominio):
                if item1.event.tipo != 17 and item1.event.cancelado == False and item1.event.id not in ids:
                    total +=  item1.event.duration
                    ids.append(item1.event.id)
            item.total_horas_planificadas = total


    def time_string_to_decimals(self, time_string):
        fields = time_string.split(":")
        hours = fields[0] if len(fields) > 0 else 0.0
        minutes = fields[1] if len(fields) > 1 else 0.0
        seconds = fields[2] if len(fields) > 2 else 0.0
        return float(hours) + (float(minutes) / 60.0) + (float(seconds) / pow(60.0, 2))       

    
    resource = fields.Many2one(comodel_name="leulit.resource", string="Recurso")
    fecha = fields.Datetime(string="Fecha", index=True)
    event_resource_lines = fields.One2many(comodel_name='leulit.event_resource', inverse_name='byday_id', string='Lineas Planificadas')
    total_horas_planificadas = fields.Float(string="Total horas imputadas", compute=_compute_total_horas_planificadas,  digits=(16, 2), compute_sudo=True, store=True)


    def upd_compute_fields(self):
        _logger.error("upd_compute_fields ")        
        model = self.env["leulit.event.resource.byday"]
        ids = [x.get('id') for x in model.search_read([], ['id'])]
        self.env.all.tocompute[model._fields['total_horas_planificadas']].update(ids)
        model.recompute()
        _logger.error("upd_compute_fields end thread")
        return {}


    def set_in_byday_event_resource(self):
        _logger.error("################### set_in_byday_event_resource ")
        threaded_calculation = threading.Thread(target=self.run_set_in_byday_event_resource, args=([]))
        _logger.error("################### set_in_byday_event_resource start thread")
        threaded_calculation.start()


    def run_set_in_byday_event_resource(self):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            for erline in self.env['leulit.event_resource'].with_context(context).sudo().search([('date','>=',"2023-01-01"),('tipo','!=',17),('cancelado','=',False)]):
                if erline.resource and erline.date:
                    erline_byday = self.env['leulit.event.resource.byday'].with_context(context).sudo().search([('resource','=',erline.resource.id),('fecha','=',erline.date)])
                    if not erline_byday:
                        erline_byday_new = self.env['leulit.event.resource.byday'].with_context(context).sudo().create({'resource':erline.resource.id,'fecha':erline.date})
                        erline.write({'byday_id':erline_byday_new.id})
                    else:
                        erline.write({'byday_id':erline_byday.id})
                    self.env.cr.commit()
            
            model = self.env["leulit.event.resource.byday"]
            ids = [x.get('id') for x in model.search_read([], ['id'])]
            self.env.all.tocompute[model._fields['total_horas_planificadas']].update(ids)
            model.recompute()
        _logger.error('################### set_in_byday_event_resource fin thread')