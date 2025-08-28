# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, date
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_piloto(models.Model):
    _name           = "leulit.piloto"
    _description    = "leulit_piloto"
    _inherits       = {'res.partner': 'partner_id'}
    _rec_name       = "name"
    _inherit        = ['mail.thread']


    @api.depends('employee_id')
    def _is_empleado_helipistas(self):
        for item in self:
            item.hlpemployee = False
            if item.employee_id:
                item.hlpemployee = True


    def _calc_airtime_piloto(self):
        strids = ','.join(str(i) for i in self.ids)
        sql = """
                SELECT piloto_id, COALESCE(SUM(airtime),0) 
                FROM leulit_vuelo 
                WHERE estado = 'cerrado' AND piloto_id IN ({0})
                GROUP BY piloto_id
            """.format(strids)
        self._cr.execute(sql)
        horas = dict(self._cr.fetchall())
        for item in self:
            item.airtime = horas.get(item.id, 0.0)


    def _calc_today(self):
        for item in self:
            today = date.today().strftime('%Y-%m-%d')
            item.hv_date = today

    def pilotoalmando(self, vuelo):
        for item in self:
            return item.id == vuelo.piloto_id.id or item.id == vuelo.verificado.id

    def copiloto(self, vuelo):
        for item in self:
            return False

    def doblemando(self, vuelo):
        for item in self:
            valor = False
            if vuelo.alumno and item.alumno:
                valor = item.alumno.id == vuelo.alumno.id and vuelo.alumno.id != vuelo.piloto_id.alumno.id
            return valor
            ##% if o.alumno.id == context['data']['form']['piloto_id'] and o.alumno.id != o.piloto_id.id:

    
    def instructor(self, vuelo):
        for item in self:
            if vuelo.alumno and vuelo.alumno.piloto.id != item.id:
                return True
            else:
                if vuelo.verificado and vuelo.verificado.id != item.id:
                    return True
        return False
     

    @api.depends('start_hv')
    def _calc_hv(self):
        for item in self:
            tiempo = item._calc_horas_totales_vuelo(item.id)
            item.hv = tiempo


    @api.depends('start_hv_pm')
    def _calc_hv_pm(self):
        for item in self:
            tiempo = item._calc_horas_piloto_almando(item.id)
            item.hv_pm = tiempo


    @api.depends('start_hv_inst')
    def _calc_hv_inst(self):
        for item in self:
            tiempo = item._calc_horas_instructor(item.id)
            item.hv_inst = tiempo
    

    @api.depends('start_hv_dm')
    def _calc_hv_dm(self):
        for item in self:
            tiempo = item._calc_horas_doblemando(item.id)
            item.hv_dm = tiempo


    @api.depends('start_hv_night_float')
    def _calc_hv_night(self):
        for item in self:
            tiempo = item._calc_horas_totales_nocturnas_vuelo(item.id)
            item.hv_night = tiempo
    
    @api.model
    def getPartnerId(self):
        return self.partner_id.id
    
    @api.depends('start_hv_ifr_float')
    def _calc_hv_ifr(self):
        for item in self:
            tiempo = item._calc_horas_totales_ifr_vuelo(item.id)
            item.hv_ifr = tiempo

    def _alumno(self):
        for item in self:
            alumno = self.env['leulit.alumno'].search([('partner_id', '=', item.getPartnerId())])
            item.alumno = alumno

    def _profesor(self):
        for item in self:
            profesor = self.env['leulit.profesor'].search([('partner_id', '=', item.getPartnerId())])
            item.profesor = profesor


    def _start_hv(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv
            item.start_hv = valor

    def _start_hv_pm(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_pm
            item.start_hv_pm = valor


    def _start_hv_inst(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_inst
            item.start_hv_inst = valor

    def _start_hv_inst(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_inst
            item.start_hv_inst = valor            

    def _start_hv_inst(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_inst
            item.start_hv_inst = valor            

    def _start_hv_dm(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_dm
            item.start_hv_dm = valor  

    def _start_hv_date(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_date
            item.start_hv_date = valor 


    def _start_hv_me(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_me
            item.start_hv_me = valor                          

    def _start_hv_se(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_se
            item.start_hv_se = valor     

    def _start_hv_night(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_night
            item.start_hv_night = valor  

    def _start_hv_ifr(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_ifr
            item.start_hv_ifr = valor 

    def _start_hv_ifr(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_ifr
            item.start_hv_ifr = valor 

    def _start_hv_me_float(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_me
            item.start_hv_me_float = valor 

    def _start_hv_se_float(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_se
            item.start_hv_se_float = valor 

    def _start_hv_night_float(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_night
            item.start_hv_night_float = valor 

    def _start_hv_ifr_float(self):
        for item in self:
            valor = 0
            hist = item.hist_16bravo.sorted(key='fecha_ini', reverse=True)
            if hist and len(hist) > 0:
                valor = hist[0].start_hv_ifr
            item.start_hv_ifr_float = valor 


    def _is_piloto_helipistas(self):
        for item in self:
            item.piloto_helipistas = False
            if 140 in item.employee.user_id.groups_id.ids or 194 in item.employee.user_id.groups_id.ids:
                item.piloto_helipistas = True

    def _search_piloto_helipistas(self, operator, value):
        ids = []
        for item in self.search([]):
            if value == True:
                if 140 in item.employee.user_id.groups_id.ids or 194 in item.employee.user_id.groups_id.ids:
                    ids.append(item.id)
            if value == False:
                if not 140 in item.employee.user_id.groups_id.ids and not 194 in item.employee.user_id.groups_id.ids:
                    ids.append(item.id)
        
        if ids:
            return [('id','in',ids)]
        return  [('id','=','0')]



    #horas iniciales piloto
    start_hv = fields.Float(compute='_start_hv', string='Horas totales inicio')
    start_hv_pm = fields.Float(compute='_start_hv_pm', string='Horas piloto al mando inicio')
    start_hv_inst = fields.Float(compute='_start_hv_inst', string='Horas instructor inicio')
    start_hv_dm = fields.Float(compute='_start_hv_dm', string='Horas doble mando inicio')
    start_hv_date = fields.Date(compute='_start_hv_date', string='Fecha inicio')
    
    #O 28/8/2017: campos date que han pasado a ser float ( los guardamos un tiempo por si necessitamos recuperar datos)
    start_hv_me = fields.Date(compute='_start_hv_me', string='Horas ME inicio')
    start_hv_se = fields.Date(compute='_start_hv_se', string='Horas SE inicio')
    start_hv_night = fields.Date(compute='_start_hv_night', string='Horas nocturnas inicio')
    start_hv_ifr = fields.Date(compute='_start_hv_ifr', string='Horas IFR inicio')
    
    start_hv_me_float = fields.Float(compute='_start_hv_me_float', string='Horas ME inicio')
    start_hv_se_float = fields.Float(compute='_start_hv_se_float', string='Horas SE inicio')
    start_hv_night_float = fields.Float(compute='_start_hv_night_float', string='Horas nocturnas inicio')
    start_hv_ifr_float = fields.Float(compute='_start_hv_ifr_float', string='Horas IFR inicio')
    
    #horas totales piloto
    hv = fields.Float(compute='_calc_hv',string='Horas totales actuales',help='Horas piloto al mando actuales')
    hv_pm = fields.Float(compute='_calc_hv_pm',string='Horas piloto al mando actuales',help='Horas piloto al mando actuales')
    hv_inst = fields.Float(compute='_calc_hv_inst',string='Horas instructor actuales',help='Horas instructor actuales')
    hv_dm = fields.Float(compute='_calc_hv_dm',string='Horas doble mando actuales',help='Horas doble mando actuales')
    hv_date = fields.Date(compute='_calc_today',string='Fecha hoy')
    hv_se = fields.Float('Horas SE totales', readonly="1")
    hv_me = fields.Float('Horas ME totales', readonly="1")
    hv_night = fields.Float(compute='_calc_hv_night',string='Horas nocturnas actuales')
    hv_ifr = fields.Float(compute='_calc_hv_ifr',string='Horas IFR actuales')
    state = fields.Selection([('activo', 'Activo'), ('baja', 'Baja')], 'Estado', required=True, default="activo")

    hist_16bravo = fields.One2many('leulit.hist_16bravo', 'piloto_id', string='Histórico 16 Bravo')
    airtime = fields.Float(compute='_calc_airtime_piloto',string='Total Airtime',help='Total Airtime')
    
    partner_id = fields.Many2one(comodel_name='res.partner', string='Contacto')
    alumno = fields.One2many(compute=_alumno, string='Alumno', comodel_name='leulit.alumno')
    profesor = fields.One2many(compute=_profesor, string='Profesor', comodel_name='leulit.profesor')
    employee = fields.Many2one(related='partner_id.user_ids.employee_id',comodel_name='hr.employee',string='Empleado')
    piloto_helipistas = fields.Boolean(compute='_is_piloto_helipistas', string='Piloto Helipistas', store=False, search='_search_piloto_helipistas')
    documentos_ids = fields.One2many(comodel_name="leulit.piloto_adjunto", inverse_name="piloto_id", string="Documentos")
    dieta_ta = fields.Float(string="Dieta Temporada Alta")
    dieta_tb = fields.Float(string="Dieta Temporada Baja")
    plus_activacion = fields.Float(string="Plus Disponibilidad/Activación")
    n_licencia = fields.Char(string="Nº Licencia")
    freelance = fields.Boolean(string="Freelance")


    ###    CALCULO HORAS TOTALES DE PILOTO AL MANDO
    def _calc_horas_piloto_almando(self):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search(['|',('piloto_id','=',item),('verificado','=',item.id),('estado','=','cerrado')]):    
                tiempo = tiempo + vuelo.tiemposervicio
            return tiempo

    ###    CALCULO HORAS TOTALES COMO INSTRUCTOR
    def _calc_horas_instructor(self, ):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search([('piloto_id','=',item.id),('verificado','!=',False),('estado','=','cerrado')]):
                if vuelo.piloto_id.id != vuelo.verificado.id:
                    if vuelo.tiemposervicio:
                        tiempo = tiempo + vuelo.tiemposervicio
            tiempo2 = 0
            for vuelo in self.env['leulit.vuelo'].search([('piloto_id','=',item.id),('alumno','!=',False),('estado','=','cerrado')]):
                if vuelo.piloto_id.getPartnerId() != vuelo.alumno.getPartnerId():
                    if vuelo.tiemposervicio:
                        tiempo2 = tiempo2 + vuelo.tiemposervicio
            tiempo = tiempo + tiempo2
            return tiempo

    ###    CALCULO HORAS TOTALES COMO DOBLEMANDO
    def _calc_horas_doblemando(self, ):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search([('alumno','=',item.id),('estado','=','cerrado')]):
                if vuelo.alumno and vuelo.alumno.getPartnerId() != vuelo.piloto_id.getPartnerId():
                    tiempo = tiempo + vuelo.tiemposervicio
            return tiempo

    ###    CALCULO HORAS TOTALES VUELO
    def _calc_horas_totales_vuelo(self, ):
        for item in self:
            ids_vuelos0 = self.env['leulit.vuelo'].search([('piloto_id','=',item.id),('estado','=','cerrado')]).ids
            ids_vuelos1 = self.env['leulit.vuelo'].search([('alumno','=',item.alumno.id),('estado','=','cerrado')]).ids
            ids_vuelos2 = self.env['leulit.vuelo'].search([('verificado','=',item.id),('estado','=','cerrado')]).ids
            tiempo = 0
            ids_vuelos = []
            for id_vuelo in ids_vuelos0:
                if not id_vuelo in ids_vuelos:
                    ids_vuelos.append(id_vuelo)
            for id_vuelo in ids_vuelos1:
                if not id_vuelo in ids_vuelos:
                    ids_vuelos.append(id_vuelo)
            for id_vuelo in ids_vuelos2:
                if not id_vuelo in ids_vuelos:
                    ids_vuelos.append(id_vuelo)
            for vuelo in self.env['leulit.vuelo'].browse(ids_vuelos):
                if vuelo.tiemposervicio:
                    tiempo = tiempo + vuelo.tiemposervicio
            return tiempo

    ### CALCULO HORAS NOCTURNAS VUELO
    def _calc_horas_totales_nocturnas_vuelo(self, ):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search([('estado','=','cerrado'),'|',('alumno','=',item.id),('piloto_id','=',item.id)]):        
                tiempo = tiempo + vuelo.night_hours
            return tiempo

    ### CALCULO HORAS IFR VUELO
    def _calc_horas_totales_ifr_vuelo(self, ):
        for item in self:
            for vuelo in self.env['leulit.vuelo'].search([('estado','=','cerrado'),'|',('alumno','=',item.alumno.id),('piloto_id','=',item.id)]):
                if vuelo.ifr:
                    tiempo = tiempo + vuelo.tiemposervicio
            return tiempo

    ###    CALCULO HORAS TOTALES DE PILOTO AL MANDO ENTRE DOS FECHAS
    def _calc_horas_piloto_almando_fechas(self, fechainicio, fechafin):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('estado','=','cerrado'),'|',('piloto_id','=',item.id),('verificado','=',item.id)]):
                tiempo = tiempo + vuelo.tiemposervicio
            return tiempo + item.start_hv_pm

    ### CALCULO HORAS NOCTURNAS VUELO FECHAS
    def _calc_horas_night_fechas(self, fechainicio, fechafin):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('estado','=','cerrado'),('nightlandings','>=',1),'|',('alumno','=',item.alumno.id),('piloto_id','=',item.id)]):
                tiempo = tiempo + vuelo.tiemposervicio
            tiempo = tiempo + item.start_hv_night_float
            return tiempo

    ### CALCULO HORAS IFR VUELO FECHAS
    def _calc_horas_ifr_fechas(self, fechainicio, fechafin):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('estado','=','cerrado'),'|',('alumno','=',item.alumno.id),('piloto_id','=',item.id)]):
                if vuelo.ifr:
                    tiempo = tiempo + vuelo.tiemposervicio
            tiempo = tiempo + item.start_hv_ifr_float
            return tiempo

    ###    CALCULO HORAS TOTALES COMO INSTRUCTOR
    def _calc_horas_instructor_fechas(self, fechainicio, fechafin):
        for item in self:
            vuelos = self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('piloto_id','=',item.id),('estado','=','cerrado'),'|',('verificado','!=',False),('alumno','!=',False)])
            tiempo = 0
            for vuelo in vuelos:
                ## --> EN EL ERPR SE UTILIZABA ESTA FUNCIÓN perfil = vueloObj.getPerfil(item)
                if item.instructor( vuelo ) and vuelo.tiempo_instuctor_actividad > 0.0:
                    tiempo = tiempo + vuelo.tiempo_instuctor_actividad
            tiempo = tiempo + item.start_hv_inst
            return tiempo 


    def _calc_horas_instructor_ato_fechas(self, fechainicio, fechafin):
        for item in self:
            vuelos = self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('piloto_id','=',item.id),('estado','=','cerrado'),'|',('verificado','!=',False),('alumno','!=',False)])
            tiempo = 0
            for vuelo in vuelos:
                ## --> EN EL ERPR SE UTILIZABA ESTA FUNCIÓN perfil = vueloObj.getPerfil(item)
                if item.instructor( vuelo ) and vuelo.tiempo_ato > 0.0:
                    tiempo = tiempo + vuelo.tiempo_ato
            return tiempo    

    ###    CALCULO HORAS TOTALES COMO DOBLEMANDO
    def _calc_horas_doblemando_fechas(self, fechainicio, fechafin):
        for item in self:
            tiempo = 0
            for vuelo in self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('alumno','=',item.alumno.id),('estado','=','cerrado')]):
                if vuelo.alumno and vuelo.alumno.getPartnerId() != vuelo.piloto_id.getPartnerId():
                    tiempo = tiempo + vuelo.tiemposervicio
            tiempo = tiempo + item.start_hv_dm
            return tiempo

    ###    CALCULO HORAS TOTALES VUELO
    def _calc_horas_totales_vuelo_fechas(self, fechainicio, fechafin):
        for item in self:
            ids_vuelos0 = self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('piloto_id','=',item.id),('estado','=','cerrado')]).ids
            ids_vuelos1 = self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('alumno','=',item.alumno.id),('estado','=','cerrado')]).ids
            ids_vuelos3 = self.env['leulit.vuelo'].search([('fechavuelo','>=',fechainicio),('fechavuelo','<',fechafin),('verificado','=',item.id),('estado','=','cerrado')]).ids
            tiempo = 0

            merged_ids = list(set(ids_vuelos0+ids_vuelos1))
            merged_ids = list(set(merged_ids+ids_vuelos3))

            '''
            for id_vuelo in ids_vuelos0:
                if not id_vuelo in ids_vuelos:
                    ids_vuelos.append(id_vuelo)
            for id_vuelo in ids_vuelos1:
                if not id_vuelo in ids_vuelos:
                    ids_vuelos.append(id_vuelo)
            for id_vuelo in ids_vuelos3:
                if not id_vuelo in ids_vuelos:
                    ids_vuelos.append(id_vuelo)
            '''
            for vuelo in self.env['leulit.vuelo'].browse(merged_ids):
                tiempo = tiempo + vuelo.tiemposervicio
            tiempotot = tiempo + item.start_hv
            
            return tiempotot


                
