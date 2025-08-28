# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)

def condition(operand, left, right):
    if operand == '=':
        operand = '=='
    return eval(' '.join((str(left),operand,str(right))))
class leulit_circular(models.Model):
    _name           = "leulit.circular"
    _description    = "leulit_circular"
    _order          = "fecha_emision desc"
    _inherit        = ['mail.thread']
    
    
    def enviarEmail(self):
        context = self.env.context.copy()
        context.update({'fecha':self.fecha_emision,
                        'autor': self.autor_id.name,
                        'area': self.area.name,
                        'nombre': self.name,
                        'descrip': self.description
                        })
        if self.fecha_fin:
            context.update({'fecha_fin': self.fecha_fin})
        else:
            context.update({'fecha_fin': '-'})
        if self.fecha_emision:
            context.update({'fecha': self.fecha_emision})
        else:
            context.update({'fecha': '-'})
        for destinatario in self.historial_ids:            
            if not destinatario.enviado:
                context.update({'mail_to': destinatario.partner_email})
                template = self.with_context(context).env.ref("leulit.leulit_circular_template")
                try:
                    template.send_mail(self.id, force_send=True, raise_exception=True)
                except Exception as e:
                    pass
                sql = "UPDATE leulit_historial_circular SET enviado = 't' WHERE id = {0}".format(destinatario.id)
                self._cr.execute(sql)


    def create_historial_circular(self):
        if self.area:
            if self.area.name == 'Alumnos Activos':
                alumnos_activos = self.env['leulit.alumno'].search([('activo','=',True)])
                for alumno in alumnos_activos:
                    existe = False
                    if not alumno.userid.employee_id:
                        if alumno.partner_id:
                            for historial in self.historial_ids:
                                if historial.partner_id.id == alumno.partner_id.id:
                                    existe = True
                            if not existe:
                                self.env['leulit.historial_circular'].create({'partner_id':alumno.partner_id.id, 'circular_id':self.id})
            else:
                empleados = self.env['hr.employee'].search([('department_id','=', self.area.id)])
                for empleado in empleados:
                    existe = False
                    if empleado.user_id:
                        if empleado.user_id.partner_id:
                            for historial in self.historial_ids:
                                if historial.partner_id.id == empleado.user_id.partner_id.id:
                                    existe = True
                            if not existe:
                                self.env['leulit.historial_circular'].create({'partner_id':empleado.user_id.partner_id.id, 'circular_id':self.id})
    

    @api.model
    def create(self, vals):
        result = super(leulit_circular, self).create(vals)
        result.create_historial_circular()
        return result


    @api.onchange('area')
    def onchange_area(self):
        for item in self:
            item.create_historial_circular()
            
        
    @api.depends('autor_id','historial_ids')
    def _is_mine(self):
        for item in self:
            item.is_mine = False
            if item.autor_id and item.autor_id.id == self.env.uid:
                item.is_mine = True
            elif item.historial_ids and len(item.historial_ids) > 0:
                for historial in item.historial_ids:
                    if historial.user_id and historial.user_id.id == self.env.uid:
                        item.is_mine = True


    def _search_is_mine(self, operator, value):
        ids = []
        for item in self.search([]):
            if item.autor_id.id == self.env.uid:
                ids.append(item.id)
            else:
                for historial_circular in item.historial_ids:
                    if historial_circular.user_id and historial_circular.user_id.id == self.env.uid:
                        ids.append(item.id)
        
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]


    @api.depends('historial_ids')
    def _pendiente(self):
        for item in self:
            item.pendiente_todos = False
            for historial in item.historial_ids:
                if not historial.recibido or not historial.leido or not historial.entendido:
                    item.pendiente_todos = True


    @api.depends('historial_ids')
    def _pendiente_mine(self):
        for item in self:
            item.pendiente = False
            for historial in item.historial_ids:
                if historial.user_id.id == self.env.uid:
                    if not historial.recibido or not historial.leido or not historial.entendido:
                        item.pendiente = True


    def _search_pendiente(self, operator, value):
        ids = []
        for item in self.search([]):
            for historial in item.historial_ids:
                if historial.user_id.id == self.env.uid:
                    if value == True:
                        if not historial.recibido or not historial.leido or not historial.entendido:
                            ids.append(item.id)
                    if value == False:
                        if historial.recibido and historial.leido and historial.entendido:
                            ids.append(item.id)
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]


    @api.depends('fecha_fin')
    def _caducada(self):
        for item in self:
            diasdiff = 0
            if item.fecha_fin:
                hoy = datetime.now()
                diasdiff = utilitylib.cal_days_diff(item.fecha_fin, hoy)
            item.caducada = diasdiff < 0


    def _search_caducada(self, operator, value):
        ids = []
        for item in self.search([]):
            diasdiff = 0
            if item.fecha_fin:
                hoy = datetime.now()
                diasdiff = utilitylib.cal_days_diff(item.fecha_fin, hoy)
                if operator == '=' and value == False:
                    if diasdiff > 0:
                        ids.append(item.id)
                if operator == '!=' and value == False:
                    if diasdiff < 0:
                        ids.append(item.id)

        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]
        

    name = fields.Char("Nombre", size=64, required=True)
    description = fields.Html("Descripción", size=100, required=True)
    fecha_emision = fields.Date("Fecha de emisión", size=64, required=False,default=fields.Date.context_today)
    fecha_fin = fields.Date("Fecha fin", size=64, required=False)
    estado = fields.Selection([('valido','Válido'),('no_valido','No válido')],"Estado", size=200, required=False)
    area = fields.Many2one('hr.department','Área',ondelete='restrict')
    area_name = fields.Char(related='area.name',string='Area',store=False)
    autor_id = fields.Many2one('res.users','Autor',ondelete='restrict', readonly='True', default=lambda self: self.env.uid)
    historial_ids = fields.One2many('leulit.historial_circular', 'circular_id', string='Circular')
    is_mine = fields.Boolean(compute='_is_mine',string='Asignada',store=False,search=_search_is_mine)
    pendiente = fields.Boolean(compute='_pendiente_mine',string='Pendiente',store=False,search=_search_pendiente)
    pendiente_todos = fields.Boolean(compute='_pendiente',string='',store=False)
    caducada = fields.Boolean(compute='_caducada',string='Caducada',store=False,search=_search_caducada)
    tipo = fields.Selection([('1', 'Genérica'),('2','Seguridad'),('3','Informativa')],'Tipo')
    