# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import date, datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_anotacion_technical_log(models.Model):
    _name   		= "leulit.anotacion_technical_log"
    _description 	= "leulit_anotacion_technical_log"
    _order  		= "fecha desc"
    _rec_name 		= "codigo"
    _inherit        = ['mail.thread']


    @api.model
    def create(self, vals):
        vals['codigo'] = self.env['ir.sequence'].next_by_code('leulit.seq.anotacion_technical_log')
        vals['informado_por'] = self.env.user.partner_id.id
        anotacion = super(leulit_anotacion_technical_log, self).create(vals)
        anotacion.wizard_send_email()
        
        return anotacion


    def unlink(self):
        if not self.env.user.has_group("leulit.RBase_hide"): 
            for item in self:
                if item.estado in ['closed','active']:
                    raise UserError('Una anotación cerrada o activa no puede ser eliminada. Pongase en contacto con el responsable de operaciones.')
        return super(leulit_anotacion_technical_log, self).unlink()


    def wizard_cerrar(self):
        self.estado = "closed"
        self.wizard_send_email()

    def wizard_activar(self):
        self.estado = "active"
        self.wizard_send_email()


    def wizard_send_email(self):
        context = self.env.context.copy()
        if self.estado == "pending":
            context.update({'subject': u' Se crea la anotación({0})'.format(self.codigo)})
        if self.estado == "active":
            context.update({'subject': u' Se activa la anotación({0})'.format(self.codigo)})
        if self.estado == "closed":
            context.update({'subject': u' Se ha cerrado la anotación ({0})'.format(self.codigo)})
        emails=['albert@icarus-manteniment.com', 'otecnica@helipistas.com']
        for emailto in emails:
            context.update({'mail_to': emailto})
            template = self.with_context(context).env.ref("leulit_seguridad.leulit_anotacion_technical_log_mail_camo_estado")
            try:
                template.send_mail(self.id, force_send=True, raise_exception=True)
            except Exception as e:
                pass


    codigo = fields.Char('Code', readonly=True)
    estado = fields.Selection([('pending', 'Pending'),('active', 'Active'),('closed', 'Closed')], 'State',default="pending")
    anotacion = fields.Text('Annotation', required=True)
    fecha = fields.Date('Date', required=True)
    informado_por = fields.Many2one('res.partner', 'Reported by', readonly=True)
    rol_informa = fields.Selection([('1','Pilot'),('2','Mechanic'),('3','CAMO'),('4','Others')],'')
    lugar = fields.Char('Place')
    helicoptero_id = fields.Many2one('leulit.helicoptero', 'Helicopter', required=True, domain="[('baja','=',False)]")

    fecha_cierre = fields.Date('Closing date')
    cerrado_por = fields.Many2one('res.partner', 'Cerrado por')
    rol_close = fields.Selection([('1', 'Pilot'), ('2', 'Mechanic'),('3','CAMO'),('4','Others')], '')
    lugar_cierre = fields.Char('Place')
    accion_cierre = fields.Text('Reason')
    

