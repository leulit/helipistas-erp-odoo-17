#-*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, date
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_helicoptero(models.Model):
    _name = "leulit.helicoptero"
    _description = "leulit_helicoptero"
    _inherit = ['mail.thread']
    
    
    @api.onchange('fechalastWB')
    def onchange_fechalastWB(self):
        self.wblastmod = date.today().strftime('%Y-%m-%d')

    
    def _get_fabricantes(self):
        return (
            ('robinson', 'Robinson'),
            ('eurocopter', 'Eurocopter'),
            ('guimbal', 'Guimbal'),
            ('dji', 'DJI')
        )


    @api.depends('fabricante')
    def _get_desc_fabricante(self):
        lista = self._get_fabricantes()
        for item in self:
            matching = [s for s in lista if item.fabricante in s]
            item.descfabricante = matching[0][1]


    @api.depends('airtimestart')
    def _calc_airtime_helicoptero(self):
        for item in self:
            horas = item.get_airtime_vuelos()
            item.airtime = horas + item.airtimestart


    @api.depends('date_tso')
    def _calc_airtime_soh_helicoptero(self):
        for item in self:
            tso = 0
            fecha_now = "{0} 23:59:59".format(datetime.now().strftime("%Y-%m-%d"))
            result = self.env['leulit.vuelo'].acumulados_between_date_and_datetime(item.id, item.date_tso, fecha_now)
            tso = result['suma_airtime']
            item.tso = tso


    def get_airtime_vuelos(self):
        result = 0
        for item in self:
            data = self.env['leulit.vuelo'].acumulados_in_date(item, datetime.now().strftime("%Y-%m-%d"))
            if data:
                result = data['airtime']
        return result


    @api.depends('landingsstart')
    def _calc_landings_helicoptero(self):
        for item in self:
            try:
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(landings + nightlandings), 0)
                    FROM leulit_vuelo
                    WHERE helicoptero_id = %s
                """, (item.id,))
                result = self.env.cr.fetchone()
                total_landings = result[0] if result else 0
                item.landings = total_landings + item.landingsstart
            except:
                item.landings = item.landingsstart


    def _calc_oil_helicoptero(self):
        for item in self:
            sql = "SELECT helicoptero_id, COALESCE(SUM(oilqty),0) FROM leulit_vuelo WHERE estado = 'cerrado' AND helicoptero_id = %r GROUP BY helicoptero_id" % ( item.id )
            self._cr.execute(sql)
            horas = dict(self._cr.fetchall())
            airtime = item.get_airtime_vuelos()
            result = horas.get(item.id, 0.0)
            if airtime > 0 :
                result = result / airtime
            item.oil = result


    def _date_last_vol(self):
        for item in self:
            vuelo = self.env['leulit.vuelo'].search([('estado','=','cerrado'), ('helicoptero_id','=',item.id)], limit=1, order='fechavuelo DESC')
            if vuelo:
                item.datelastflight = vuelo.fechavuelo.strftime("%d-%m-%Y")
            else:
                item.datelastflight = ''

    
    @api.depends('fechaproximarev')
    def _calc_dias_vuelo_restantes(self):
        for item in self:
            fechaproximarev = item.fechaproximarev
            if not item.fechaproximarev:
                fechaproximarev = datetime.now().date()
            item.dias_remanente = (fechaproximarev - datetime.now().date()).days


    @api.depends('proximarev','airtime')
    def _calc_horas_vuelo_restantes(self):
        for item in self:
            item.horas_remanente = item.proximarev - item.airtime

    
    @api.depends('horas_remanente')
    def _get_str_horas(self):
        for item in self:
            item.strhoras_remanente = utilitylib.leulit_float_time_to_str(item.horas_remanente)
    

    def check_semaforo(self):
        if self.horas_remanente <= 0.5 or self.statemachine == 'En taller':
            return 'red'
        elif self.horas_remanente <= 10:
            return 'yellow'
        else:
            return 'green'


    def check_semaforo_fecha(self):
        if self.dias_remanente <= 15 or self.statemachine == 'En taller':
            return 'red'
        elif self.dias_remanente <= 30:
            return 'yellow'
        else:
            return 'green'


    def _get_semaforo(self):
        for item in self:
            item.semaforo = item.check_semaforo()


    def _get_semaforo_fecha(self):
        for item in self:
            item.semaforo_fecha = item.check_semaforo_fecha()



    fabricante = fields.Selection(_get_fabricantes,'Fabricante',required=True)
    descfabricante = fields.Char(compute='_get_desc_fabricante',string='Descripción fabricante')
    modelo = fields.Many2one('leulit.modelohelicoptero', 'Modelo', required=True) 
    tipo = fields.Selection(related='modelo.tipo',string='Tipo',store=False)
    pesomax = fields.Float(related='modelo.pesomax',string='Peso Máximo (kg)',store=False)
    name = fields.Char('Matrícula', size=20,required=True)
    serialnum = fields.Char('Número de serie',size=10)
    owner = fields.Char('Propietario', size=20)
    fechafab = fields.Date('Fecha fabricación')
    fechalastWB = fields.Date('Fecha último W&B')
    fechafhm = fields.Date('Actualización FHM')
    velocidad = fields.Float('Velocidad crucero (KT)')
    consumomedio = fields.Float('Consumo medio (l/m)')
    codoperador = fields.Char('Código operador', size=20)
    horasohmotor = fields.Float('Horas OH')
    fechaohmotor = fields.Date('Fecha OH')
    doitovmotor = fields.Boolean('Realización OH motor',default=False)
    doitov = fields.Boolean('Realización OH',default=False)
    airtimestart = fields.Float('Horas vuelo inicio (hh:mm)', required=True)
    airtime = fields.Float(compute='_calc_airtime_helicoptero',string='Total Airtime - TSN (hh:mm)',store=False)
    date_tso = fields.Date(string='Fecha OH')
    tso = fields.Float(compute='_calc_airtime_soh_helicoptero',string='Total Airtime - TSO (hh:mm)',store=False)
    landingsstart = fields.Integer('Landings inicio', required=True)
    landings = fields.Integer(compute='_calc_landings_helicoptero',string='Total Landings',store=False)
    oil = fields.Float(compute='_calc_oil_helicoptero',string='Oil (l/h)',store=False)
    proximarev = fields.Float('Horas proxima revisión (hh:mm)')
    fechaproximarev = fields.Date('Fecha próxima revisión')
    caducidadseguro = fields.Date('Fecha caducidad seguro')
    ctrlmantenimiento = fields.Boolean('Gestión mantenimiento',default=True)
    ctrloperaciones = fields.Boolean('Gestión operación')
    ctrlcamo = fields.Boolean('Gestión CAMO')
    statemachine = fields.Selection([('En servicio', 'En servicio'),('En taller', 'En taller')],'Situación máquina',required=True)
    datelastflight = fields.Char(compute='_date_last_vol',string='Última operación',store=False)
    emptyweight = fields.Float('Peso en vacío (kg.)', required=True)
    longmoment = fields.Float('Long moment (cm.kg)')
    longarm = fields.Float('CG. Long. (cm)', required=True)
    latmoment = fields.Float('Lat. moment (cm.kg)')
    latarm = fields.Float('CG. Lat. (cm.)', required=True)
    wblastmod = fields.Date('Fecha modificación W&B')
    dias_remanente = fields.Integer(compute='_calc_dias_vuelo_restantes',string='Dias vuelo restantes')
    horas_remanente = fields.Float(compute='_calc_horas_vuelo_restantes',string='Horas vuelo restantes')
    strhoras_remanente = fields.Char(compute='_get_str_horas',string='Horas vuelo restantes st')
    colormarks = fields.Char('Color/marcas', size=250, required=True)
    semaforo = fields.Char(compute='_get_semaforo',string='Semaforo',store=False)
    semaforo_fecha = fields.Char(compute='_get_semaforo_fecha',string='Fecha semaforo',store=False)
    write_uid = fields.Many2one('res.users', 'by User', readonly=False)
    me = fields.Boolean('ME')
    se = fields.Boolean('SE')
    baja = fields.Boolean('Baja',default=False)
    is_privado = fields.Boolean('Privado')
    pformacion_id = fields.Many2one('leulit.helicoptero', 'Perfil Formación', readonly=False)
    ubicacion = fields.Many2one('stock.location', 'Ubicación')
    