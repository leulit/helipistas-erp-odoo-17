# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import date, datetime, timedelta
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_anomalia(models.Model):
    _name   		= "leulit.anomalia"
    _description 	= "leulit_anomalia"
    _order  		= "fecha desc, vuelo_id desc"
    _rec_name 		= "codigo"
    _inherit        = ['mail.thread']


    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('leulit.seq.anomalia')
        vals['codigo'] = sequence
        vals['informado_por'] = self.env.user.partner_id.id
        if 'default_vuelo_id' in self.env.context:
            item = self.env['leulit.vuelo'].browse(self.env.context['default_vuelo_id'])
            vals.update({'helicoptero_id': item.helicoptero_id.id })
            vals.update({'vuelo_id': item.id })

        anomalia = super(leulit_anomalia, self).create(vals)
         
        return anomalia


    def unlink(self):
        if not self.env.user.has_group("leulit.RBase_hide"): 
            for item in self:
                if item.estado in ['closed','flightcanceled','pending','deferred']:
                    raise UserError('Una anomalía/discrepancia cerrada, pendiente o diferida no puede ser eliminada. Pongase en contacto con el responsable de operaciones.')
        return super(leulit_anomalia, self).unlink()


    def wizard_diferir(self):
        for item in self:
            if not item.motivodiferir:
                raise UserError('Es obligatorio indicar el motivo por el cual se difiere la anomalía/defecto')
            if item.melref:
                if not item.categoria:
                    raise UserError('Debe indicar la categoría junto con la referencia mel para poder diferir la anomalía/defecto')
            if item.categoria and not item.melref:
                raise UserError('Debe indicar la referencia mel junto con la categoria para poder diferir la anomalía/defecto')
            descripcion = "{0} - {1}".format(item.id,item.discrepancia)
            if not item.fechadiferido:
                fecha = datetime.now()
            else:
                fecha = item.fechadiferido
            referencia ="{0}-ANOMALIA".format(item.id)
            self.prepareSignature(descripcion, referencia, "leulit.anomalia", item.id, fecha)
            item.write({ 'estado' : 'deferred', 'fechadiferido': fecha, 'diferido_por':self.env.user.partner_id.id, 'date_deferred':datetime.now() })
            item.wizard_send_email()


    def wizard_pending(self):
        for item in self:
            item.estado = 'pending'
            item.wizard_send_email()


    def wizard_cerrar(self):
        for item in self:
            if not item.accion:
                raise UserError('Es obligatorio indicar la acción para cerrar la anomalía/defecto')
            item.hora_cierre = utilitylib.leulit_datetime_to_float_time(datetime.now())
            descripcion = "{0} - {1}".format(item.id,item.discrepancia)
            if not item.fecha_accion:
                fecha = datetime.now()
            else:
                fecha = item.fecha_accion
            referencia ="{0}-ANOMALIA".format(item.id)
            item.write({ 'estado' : 'closed', 'fecha_accion': fecha, 'cerrado_por':self.env.user.partner_id.id, 'date_closed':datetime.now() })
            

    def wizard_send_email(self):
        estado = self.estado
        context = self.env.context.copy()
        if self.baja_helicoptero == False:
            if estado == "pending":
                context.update({'subject': u' Se ha creado una anomalía/defecto ({0})'.format(self.codigo)})
            if estado == "deferred":
                context.update({'subject': u' Se ha diferido una anomalía/defecto ({0})'.format(self.codigo)})
            if estado == "closed":
                context.update({'subject': u' Se ha cerrado una anomalía/defecto ({0})'.format(self.codigo)})
            if estado == "flightcanceled":
                context.update({'subject': u' Se ha cancelado un vuelo debido a una anomalía/defecto ({0})'.format(self.codigo)})
            emails=['erpanomalias@helipistas.com', 'otecnica@helipistas.com']
            for emailto in emails:
                context.update({'mail_to': emailto})
                template = self.with_context(context).env.ref("leulit_seguridad.leulit_anomalia_mail_camo_estado")
                try:
                    template.send_mail(self.id, force_send=True, raise_exception=True)
                except Exception as e:
                    pass
                

    def get_diferidos_by_fechas(self, from_date, to_date):
        return self.search([
             ('estado', 'in',['pending', 'deferred', 'flightcanceled', 'closed']),
             ('fecha', '>=', from_date),
             ('fecha', '<=', to_date)])


    def get_diferidos_by_fecha(self, fecha):
        return self.search([('estado','in',['pending','deferred','flightcanceled','closed']),('fecha','=',fecha)])


    def calc_fecha_limite(self, categoria, fecha):
        valor = fecha
        if categoria == 'A' :
            valor1 =  (fecha + timedelta(days=365))
            valor = valor1.strftime("%Y-%m-%d")
        if categoria == 'B' :
            valor1 =  (fecha + timedelta(days=3))
            valor = valor1.strftime("%Y-%m-%d")
        if categoria == 'C' :
            valor1 =  (fecha + timedelta(days=10))
            valor = valor1.strftime("%Y-%m-%d")
        if categoria == 'D' :
            valor1 = (fecha + timedelta(days=120))
            valor = valor1.strftime("%Y-%m-%d")
        return valor


    @api.onchange('melref')
    def change_refmel(self):
        items = self.env['leulit.lines_mel'].search([('mel_id','=',self.melref.id)])
        return {'domain':{'linemel_id':[('id','in',items.ids)]}}


    @api.onchange('categoria','fecha')
    def change_categoria(self):
        res = False
        for item in self:
            res =  item.calc_fecha_limite(item.categoria, item.fecha)
            item.fechalimite = res


    @api.onchange('linemel_id')
    def change_linemel_id(self):
        if self.linemel_id:
            self.tipomel = self.linemel_id.tipo.id
            self.categoria = self.linemel_id.categoria
            self.numinstaladomel = self.linemel_id.numinstalado
            self.numexpmel = self.linemel_id.numexp
            self.tenerencuentamel = self.linemel_id.tenerencuenta


    @api.depends('airtime')
    def _get_str_horas(self):
        valor = 0
        for item in self:
            item.strairtime = utilitylib.leulit_float_time_to_str( item.airtime )
            

    @api.onchange('helicoptero_id')
    def onchange_helicoptero(self):
        domain_ids = []
        if self.helicoptero_id:
            for equipment in self.env['maintenance.equipment'].search([('helicoptero','=',self.helicoptero_id.id)]):
                for id in equipment.get_childs().ids:
                    domain_ids.append(id)
        self.write({'domain_materiales' :[(6,0,domain_ids)]})


    @api.onchange('vuelo_id')
    def onchange_updvuelo(self):
        for item in self:
            if item.vuelo_id:
                item.helicoptero_id = item.vuelo_id.helicoptero_id
            else:
                item.helicoptero_id = False

    def edit_anomalia(self):
        self.ensure_one()
        view = self.env.ref('leulit_seguridad.leulit_20201026_0823_form',raise_if_not_found=False)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Anomalía',
            'res_model': 'leulit.anomalia',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': view.id if view else False,
            'target': 'current',
        }

    
    @api.depends('fecha','date_deferred')
    def _get_days_between_create_deferred(self):
        for item in self:
            item.days_deferred = -1
            if item.create_date and item.date_deferred:
                item.days_deferred = (item.date_deferred.date()-item.fecha).days


    @api.depends('fecha','date_closed')
    def _get_days_between_create_close(self):
        for item in self:
            item.days_close = -1
            if item.create_date and item.date_closed:
                item.days_close = (item.date_closed.date()-item.fecha).days


    codigo = fields.Char('Código', size=20,readonly=True)
    melref = fields.Many2one('leulit.mel', 'Ref. Description')
    linemel_id = fields.Many2one('leulit.lines_mel', 'Reference')
    tipomel = fields.Many2one('leulit.mel_tipo_operacion', 'Kind', readonly=True)
    categoria = fields.Char('Category', size=2, readonly=True)
    numinstaladomel = fields.Integer('Nº installed', readonly=True)
    numexpmel = fields.Char('Nº expedition', size=20, readonly=True)
    pom = fields.Selection([('Sí','Sí'),('No','No')],'POM')
    limita = fields.Selection([('Sí', 'Sí'), ('No', 'No')], 'POM')
    tenerencuentamel = fields.Text('POI / Exceptions',)
    fechalimite = fields.Date('Dead date')
    fechadiferido = fields.Date('Fecha diferido', readonly=True)
    rol_informa = fields.Selection([('1','Pilot'),('2','Mechanic')],'')
    rol_difiere = fields.Selection([('1', 'Pilot'),('2', 'Mechanic')], '')
    rol_close = fields.Selection([('1', 'Pilot'), ('2', 'Mechanic')], '')
    lugaranomalia = fields.Char('Lugar anomalía')
    fecha_crs = fields.Date('Fecha CRS')

    discrepancia = fields.Text('Discrepancia/Anomalía', required=True)
    motivodiferir = fields.Text('Acción considerada')
    comentario = fields.Char('Comentario', size=200)
    lugar_crs = fields.Char('Lugar CRS', size=200)
    comentario_crs = fields.Char('Comentario CRS')
    fecha = fields.Date('Fecha', required=True, readonly=True)

    crs_por = fields.Many2one('res.partner', 'CRS por', readonly=True)
    firma_crs_por = fields.Binary(related='crs_por.firma',string='Firma CRS por')
    sello_crs_por = fields.Binary(related='crs_por.sello',string='Sello CRS por')

    informado_por = fields.Many2one('res.partner', 'Informado por', readonly=True)
    firma_informado_por = fields.Binary(related='informado_por.firma',string='Firma informado por')
    sello_informado_por = fields.Binary(related='informado_por.sello',string='Sello informado por')

    diferido_por = fields.Many2one('res.partner', 'Diferido por', readonly=True)
    firma_diferido_por = fields.Binary(related='diferido_por.firma',string='Firma diferido por')
    sello_diferido_por = fields.Binary(related='diferido_por.sello',string='Sello diferido por')
    date_deferred = fields.Datetime(string="Deferred", readonly=False)
    days_deferred = fields.Integer(compute=_get_days_between_create_deferred, stirng="Days to deferred", store=False)

    cerrado_por = fields.Many2one('res.partner', 'Cerrado por', readonly=True)
    cerrado_por_company = fields.Char(related='cerrado_por.company_id.name',string='Compañía')
    firma_cerrado_por = fields.Binary(related='cerrado_por.firma',string='Firma cerrado por')
    sello_cerrado_por = fields.Binary(related='cerrado_por.sello',string='Sello cerrado por')
    date_closed = fields.Datetime(string="Closed", readonly=False)
    days_close = fields.Integer(compute=_get_days_between_create_close, stirng="Days to Close", store=False)

    cancelado_por = fields.Many2one('res.partner', 'Cancelado por', readonly=True)
    firma_cancelado_por = fields.Binary(related='cancelado_por.firma',string='Firma cancelado por')
    sello_cancelado_por = fields.Binary(related='cancelado_por.sello',string='Sello cancelado por')

    fecha_cancelado = fields.Date('Fecha cancelado')
    accion = fields.Text('Motivo cierre')
    fecha_accion = fields.Date('Fecha cierre')
    hora_cierre = fields.Float('Hora cierre')
    cas = fields.Char('CAS', size=255)

    vuelo_id = fields.Many2one('leulit.vuelo','Vuelo origen')

    helicoptero_id = fields.Many2one('leulit.helicoptero', 'Helicoptero', required=True, domain="[('baja','=',False)]")
    baja_helicoptero = fields.Boolean(related='helicoptero_id.baja',string='Baja helicóptero',store=False)
    fabricante = fields.Selection(related='helicoptero_id.fabricante',string='Fabricante',store=False)

    airtime = fields.Float('Airtime')
    strairtime = fields.Char(compute='_get_str_horas',string='StrAirtime')
    estado = fields.Selection([('edicion', 'En edición'),('pending', 'Pendiente'),('deferred', 'Diferido'),('closed', 'Cerrado'),('flightcanceled', 'Vuelo cancelado'),], 'Estado',default="edicion")

    fechavuelo = fields.Date(related='vuelo_id.fechavuelo',string='Fecha',store=False)
    lugarllegada = fields.Many2one(related='vuelo_id.lugarllegada',comodel_name="leulit.helipuerto",string='Lugar llegada',store=False)
    lugarsalida = fields.Many2one(related='vuelo_id.lugarsalida',comodel_name="leulit.helipuerto",string='Lugar salida',store=False)
    horasalida = fields.Float(related='vuelo_id.horasalida',string='Hora salida',store=False)
    horallegada = fields.Float(related='vuelo_id.horallegada',string='Hora llegada',store=False)
    oilqty = fields.Float(related='vuelo_id.oilqty',string='oil qty',store=False)
    fuelqty = fields.Float(related='vuelo_id.fuelqty',string='fuel qty',store=False)
    consumomedio_vuelo = fields.Float(related='vuelo_id.consumomedio_vuelo',string='Consumo medio vuelo',store=False)
    fuelsalida_kg = fields.Float(related='vuelo_id.fuelsalida_kg',string='fuel salida (Kg)',store=False)

    materiales_equipments = fields.Many2many('maintenance.equipment', 'rel_equipment_anomalia', 'anomalia', 'equipment', 'Materiales')
    domain_materiales = fields.One2many('maintenance.equipment','anomalia',string="domain materiales")
    notificacion_sms = fields.Text('Notificación al SMS')

    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Orden de trabajo")

