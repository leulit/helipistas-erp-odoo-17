# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp
import threading
from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)


class leulit_actividad_base(models.Model):
    _name = "leulit.actividad_base"
    _description = "leulit_actividad_base"
    _order = "fecha desc, inicio asc, partner"
    _rec_name = "descripcion"

    _time_pre_vuelo = 0.75
    _time_post_vuelo = 0.5

    _tiempo_maximo_vuelo = {
        'AOC'               : 3.0,
        'Trabajo Aereo'     : 3.0,
        'LCI'               : 3.0,
        'Escuela'           : 3
    }

    def get_valid_flight_time(self, tipo, tiempo):
        valor = "N.A."
        if tipo in self._tiempo_maximo_vuelo:
            result = round(float(tiempo),2) <= round(float(self._tiempo_maximo_vuelo[tipo]),2)
            valor = "green" if result else "red"
        return valor


    def getId(self, datos):
        item = self.search([('idmodelo','=', datos['idmodelo']), ('modelo','=',datos['modelo']), ('partner','=',datos['partner'])])
        _logger.error("-->> actividad_base getid item = %r",item)
        if len(item) > 0:
            return item
        else:
            return self.create({'idmodelo': datos['idmodelo'], 'modelo': datos['modelo'], 'partner': datos['partner']})

    def calc_coe_mayoracion(self, fechavuelo, horallegada, partner, ato, escuela):
        nrows = self.search([
                    ('fecha','=',fechavuelo),
                    ('partner', '=', partner),
                    ('inicio','>=',horallegada),
                    ('modelo','=','helipistas.vuelo'),
                ],count=True)
        return 1.5 if ((nrows > 0) and escuela and (not ato)) else 1


    def calc_delta_pre(self, fechavuelo, partner, inicio):
        nrows = self.search([
                    ('fecha','=',fechavuelo),
                    ('partner', '=', partner),
                    ('fin','<=',inicio),
                    ('modelo','=','helipistas.vuelo'),
                ],count=True)
        if (nrows > 0):
            return 0
        else:
            sql = '''
                UPDATE
                    leulit_actividad_base
                SET
                    delta_pre = 0
                WHERE
                    fecha = '{0}'::DATE
                AND
                    partner = {1}
                AND
                    modelo = 'leulit.vuelo'
            '''.format(fechavuelo, partner)
            self._cr.execute(sql)
            return self._time_pre_vuelo


    def calc_delta_pos(self, fechavuelo, partner, fin):
        nrows = self.search([
                    ('fecha','=',fechavuelo),
                    ('partner', '=', partner),
                    ('inicio','>=',fin),
                    ('modelo','=','helipistas.vuelo'),
                ],count=True)
        if (nrows > 0):
            return 0
        else:
            sql = '''
                UPDATE
                    leulit_actividad_base
                SET
                    delta_pos = 0
                WHERE
                    fecha = '{0}'::DATE
                AND
                    partner = {1}
                AND
                    modelo = 'leulit.vuelo'
            '''.format(fechavuelo, partner)
            self._cr.execute(sql)
            return self._time_post_vuelo


    def delPrevData(self, fecha):
        hoy = utilitylib.getStrToday() 
        sql = """
            DELETE FROM leulit_actividad_base 
            WHERE 
                    fecha <= '{0}'::DATE 
                AND
                    prevista = 't'
        """.format(hoy)
        self._cr.execute(sql)

    # def getTareaRepetida(self, fecha, user, inicio, fin):
    #     items = self.search([('fecha','=',fecha), ('partner','=',user), ('inicio','=',inicio), ('fin','=',fin)])    
    #     if items and len(items) > 0:
    #         return self.browse(items[0])
    #     else:
    #         return False

    def updateWithVueloData(self, data, partners, ato):
        datos = {}
        if data.estado and data.estado == 'cerrado':
            _logger.error('######### --updDataActividad-- >>')
            escuela = True if data.parte_escuela_id else False
            for partner in partners:
                _logger.error('######### --updDataActividad-- >> %r',partner)
                self.delPrevData(data.fechavuelo)
                _logger.error('######### --updDataActividad-- >>')
                coe_mayoracion = self.calc_coe_mayoracion(data.fechavuelo, data.horallegada, partner['id'], ato, escuela)
                delta_pre = self.calc_delta_pre(data.fechavuelo, partner['id'], data.horasalida)
                delta_pos = self.calc_delta_pos(data.fechavuelo, partner['id'], data.horallegada)
                item1 = self.get_valid_flight_time(data.tipo_actividad, data.tiemposervicio)
                _logger.error('######### --updDataActividad-- >> %r',item1)
                item2 = self.env['leulit.actividad_16bravo'].getId(data.fechavuelo, partner['id'])
                _logger.error('######### --updDataActividad-- >> %r',item2)
                item3 = self.env['leulit.actividad_16bravo_dia'].getId(data.fechavuelo, partner['id'])
                _logger.error('######### --updDataActividad-- >> %r',item3)
                datos = {
                    'fecha'                         : data.fechavuelo,
                    'fecha_inicio'                  : datetime.strptime(utilitylib.get_date_time_str(data.fechavuelo, data.horasalida), utilitylib.STD_DATETIME_FORMAT),
                    'fecha_fin'                     : datetime.strptime(utilitylib.get_date_time_str(data.fechavuelo, data.horallegada), utilitylib.STD_DATETIME_FORMAT),        
                    'idmodelo'                      : data.id,
                    'modelo'                        : 'leulit.vuelo',
                    'inicio'                        : data.horasalida,
                    'fin'                           : data.horallegada,
                    'delta_pre'                     : delta_pre,
                    'delta_pos'                     : delta_pos,
                    'tiempo_calc'                   : (data.tiemposervicio*coe_mayoracion)+delta_pre+delta_pos,
                    'tiempo'                        : data.tiemposervicio,
                    'actividad_aerea'               : True,
                    'prevista'                      : False,
                    'partner'                       : partner['id'],
                    'rol'                           : partner['rol'],
                    'descripcion'                   : data.codigo,
                    'tipo_actividad'                : data.tipo_actividad,
                    'escuela'                       : escuela,
                    'ato'                           : ato,
                    'coe_mayoracion'                : coe_mayoracion,
                    'valid_flight_time'             : self.get_valid_flight_time(data.tipo_actividad, data.tiemposervicio),
                    'actividad_16bravo_id'          : self.env['leulit.actividad_16bravo'].getId(data.fechavuelo, partner['id']),
                    'actividad_16bravo_dia_id'      : self.env['leulit.actividad_16bravo_dia'].getId(data.fechavuelo, partner['id'])
                }
                _logger.error('######### --updDataActividad-- >> %r',datos)
                item = self.getId(datos)
                _logger.error('######### --updDataActividad-- >> %r',item)
                item.write(datos)
                datos['id'] = item.id
        return datos
 
    @api.model
    def updateWithEscuelaData(self, data, ato):
        datos = {}
        if data.estado and data.estado == 'cerrado':            
            self.delPrevData(data.fecha)
            _logger.error("-- >> updateWithEscuelaData data = %r",data)
            datos = {
                'fecha'                         : data.fecha,
                'fecha_inicio'                  : datetime.strptime(utilitylib.get_date_time_str(data.fecha, data.hora_start), utilitylib.STD_DATETIME_FORMAT),
                'fecha_fin'                     : datetime.strptime(utilitylib.get_date_time_str(data.fecha, data.hora_end), utilitylib.STD_DATETIME_FORMAT),        
                'idmodelo'                      : data.id,
                'modelo'                        : 'helipistas.parte_escuela',
                'inicio'                        : data.hora_start,
                'fin'                           : data.hora_end,
                'tiempo_calc'                   : data.tiempo,
                'tiempo_calc_laboral'           : data.tiempo,
                'tiempo'                        : data.tiempo,
                'actividad_aerea'               : False,
                'prevista'                      : False,
                'partner'                       : data.profesor.getPartnerId(),
                'rol'                           : "profesor",
                'descripcion'                   : data.name,
                'tipo_actividad'                : "clase_teorica",
                'escuela'                       : True,
                'ato'                           : ato,
                'coe_mayoracion'                : 1,
                'valid_flight_time'             : "N.A.",
            }
            item = self.getId(datos)
            _logger.error("-- >> updateWithEscuelaData iditem = %r",item)
            _logger.error("-- >> updateWithEscuelaData iditem = %r",datos)
            item.write(datos)
            datos['id'] = item.id
        return datos





    # def updateWithTareaData(self, data, context):
    #     self.delPrevData(data.fecha, context)
    #     datos = {
    #         'fecha'                         : data.fecha,
    #         'fecha_inicio'                  : self.get_date_time_str(data.fecha, data.hora_inicio),
    #         'fecha_fin'                     : self.get_date_time_str(data.fecha, data.hora_fin),        
    #         'idmodelo'                      : data.id,
    #         'modelo'                        : 'helipistas.tarea.tiempo',
    #         'inicio'                        : data.hora_inicio,
    #         'fin'                           : data.hora_fin,
    #         'tiempo_calc'                   : data.tiempo,
    #         'tiempo'                        : data.tiempo,
    #         'actividad_aerea'               : data.actvuelo,
    #         'prevista'                      : False,
    #         'partner'                       : data.partner.id,
    #         'rol'                           : "trabajador",
    #         'descripcion'                   : data.name,
    #         'tipo_actividad'                : "tarea_tiempo",
    #         'escuela'                       : False,
    #         'ato'                           : False,
    #         'coe_mayoracion'                : 1,
    #         'valid_flight_time'             : "N.A.",            
    #     }
    #     # iditem = self.getTareaRepetida(datos['fecha'], datos['partner'], datos['inicio'], datos['fin'])
    #     #if iditem > 0:
    #     #    self.unlink(cr, )
    #     iditem = self.getId(datos, context)                
    #     self.write(iditem, datos, context)
    #     datos['id'] = iditem
    #     return datos    


    # def updateWithPilotoTareaData(self, data, context):        
    #     self.delPrevData(data.fecha, context)
    #     datos = {
    #         'fecha'                         : data.fecha,
    #         'fecha_inicio'                  : self.get_date_time_str(data.fecha, data.horainicio),
    #         'fecha_fin'                     : self.get_date_time_str(data.fecha, data.horafin),        
    #         'idmodelo'                      : data.id,
    #         'modelo'                        : 'helipistas.piloto.tarea',
    #         'inicio'                        : data.horainicio,
    #         'fin'                           : data.horafin,
    #         'tiempo_calc'                   : data.tiempo,
    #         'tiempo'                        : data.tiempo,
    #         'actividad_aerea'               : data.actvuelo,
    #         'prevista'                      : False,
    #         'partner'                       : data.partner.id,
    #         'rol'                           : "trabajador",
    #         'descripcion'                   : data.name.name,
    #         'tipo_actividad'                : "piloto_tarea",
    #         'escuela'                       : False,
    #         'ato'                           : False,
    #         'coe_mayoracion'                : 1,
    #         'valid_flight_time'             : "N.A.",            
    #     }
    #     if not self.getTareaRepetida(datos['fecha'], datos['partner'], datos['inicio'], datos['fin']):
    #         iditem = self.getId(datos, context)                
    #         self.write(iditem, datos, context)
    #         datos['id'] = iditem
    #     return datos            


    # def updateWithTallerTareaData(self, data, context):
    #     self.delPrevData(data.fecha, context)
    #     datos = {
    #         'fecha'                         : data.fecha,
    #         'fecha_inicio'                  : self.get_date_time_str(data.fecha, data.hora_inicio),
    #         'fecha_fin'                     : self.get_date_time_str(data.fecha, data.hora_fin),        
    #         'idmodelo'                      : data.id,
    #         'modelo'                        : 'helipistas.taller.tarea',
    #         'inicio'                        : data.hora_inicio,
    #         'fin'                           : data.hora_fin,
    #         'tiempo_calc'                   : data.tiempo,
    #         'tiempo'                        : data.tiempo,
    #         'actividad_aerea'               : False,
    #         'prevista'                      : False,
    #         'partner'                       : data.partner.id,
    #         'rol'                           : "trabajador",
    #         'descripcion'                   : data.name,
    #         'tipo_actividad'                : "taller_tarea",
    #         'escuela'                       : False,
    #         'ato'                           : False,
    #         'coe_mayoracion'                : 1,
    #         'valid_flight_time'             : "N.A.",
    #     }
    #     if self.getTareaRepetida(datos['fecha'], datos['partner'], datos['inicio'], datos['fin']):
    #         iditem = self.getId(datos, context)                
    #         self.write(iditem, datos, context)
    #         datos['id'] = iditem
    #     return datos  


    # def updatePlanifData(self, data, partner, isRolAA, context):
    #     self.delPrevData(data.fecha_ini, context)
    #     datos = {
    #         'fecha'                         : data.fecha_ini,
    #         'fecha_inicio'                  : self.get_date_time_str(data.fecha_ini, data.hora_inicio_evento),
    #         'fecha_fin'                     : self.get_date_time_str(data.fecha_ini, data.hora_fin_evento),        
    #         'idmodelo'                      : data.id,
    #         'modelo'                        : 'crm.meeting',
    #         'inicio'                        : data.hora_inicio_evento,
    #         'fin'                           : data.hora_fin_evento,
    #         'tiempo_calc'                   : data.duration,
    #         'tiempo'                        : data.duration,
    #         'actividad_aerea'               : isRolAA,
    #         'prevista'                      : True,
    #         'partner'                       : partner,
    #         'rol'                           : 'rolaa_evento' if isRolAA else 'no_rolaa_evento',
    #         'descripcion'                   : data.name,
    #         'tipo_actividad'                : "planificada",
    #         'escuela'                       : False,
    #         'ato'                           : False,
    #         'coe_mayoracion'                : 1,
    #         'valid_flight_time'             : "N.A.",
    #     }
    #     iditem = self.getId(datos, context)                
    #     self.write(iditem, datos, context)
    #     datos['id'] = iditem
    #     return datos                  



    fecha = fields.Date('Fecha', index=True)
    fecha_inicio = fields.Datetime('Fecha inicio', index=True)
    fecha_fin = fields.Datetime('Fecha fin', index=True)
    idmodelo = fields.Integer('idmodelo', index=True)
    modelo = fields.Char('Modelo', index=True)
    inicio = fields.Float('Inicio actividad', digits=(16, 2))
    fin = fields.Float('Fin actividad', digits=(16, 2))
    delta_pre = fields.Float('Delta previo', digits=(16, 2))
    delta_pos = fields.Float('Delta post', digits=(16, 2))
    tiempo_calc = fields.Float("Tiempo actividad calculado", digits=(16, 2))
    tiempo_calc_laboral = fields.Float("Tiempo actividad laboral calculado", digits=(16, 2))
    tiempo = fields.Float("Tiempo actividad", digits=(16, 2))
    actividad_aerea = fields.Boolean('Es actividad aérea')
    prevista = fields.Boolean('Prevista')
    escuela = fields.Boolean('Escuela')
    ato = fields.Boolean('ATO')
    coe_mayoracion = fields.Float('Coeficiente mayoración')
    partner = fields.Many2one('res.partner', 'Empleado Helipistas', ondelete='restrict', index=True)
    rol = fields.Char('Rol empleado')
    descripcion = fields.Char('Descripción')
    tipo_actividad = fields.Char('Tipo actividad')
    valid_flight_time = fields.Char('Semáforo tiempo de vuelo')
    actividad_16bravo_id = fields.Many2one("leulit.actividad_16bravo", "Actividad 16Bravo", ondelete='cascade', index=True)
    actividad_16bravo_dia_id = fields.Many2one("leulit.actividad_16bravo_dia", "Actividad 16Bravo día", ondelete='cascade', index=True)
    actividad_base_dia_id = fields.Many2one("leulit.actividad_base_dia", "Actividad base día", ondelete='cascade', index=True)


    def detalle(self):
        return True
        # TODO
        # if context is None:
        #     context = {}
        # item = self.read(cr, uid, ids, [])[0]
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Item actividad',
        #     'res_model': item['modelo'],
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'res_id': item['idmodelo'],
        #     'context': context,
        #     'initial_mode': 'view',
        #     'target': 'self',
        # }



    @api.model
    def data_calculation(self, fecha_inicio="", fecha_fin=""):
        _logger.error("data_calculation ")        
        threaded_calculation = threading.Thread(target=self.do_data_calculation, args=([fecha_inicio, fecha_fin]))
        _logger.error("data_calculation start thread")
        threaded_calculation.start()        
        return {}    


    def do_data_calculation(self, fecha_inicio, fecha_fin):
        """
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the partner currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        """           
        with api.Environment.manage():
            _logger.error("do_data_calculation build new_cr")
            new_cr = registry(self._cr.dbname).cursor()
            new_cr.autocommit(True)
            self = self.with_env(self.env(cr=new_cr)).with_context(original_cr=self._cr)

            #new_cr = self.pool.cursor()
            #self = self.with_env(self.env(cr=new_cr))
            self.env.cr.autocommit(True) 
            try:
                _logger.error('16BTH -> START THREAD')
                _logger.error('16BTH -> START THREAD ---> %r',fecha_inicio)
                _logger.error('16BTH -> START THREAD ---> %r',fecha_fin)

                sdate = utilitylib.str_date_to_date(fecha_inicio)
                edate = utilitylib.str_date_to_date(fecha_fin)
                delta = edate - sdate 

                fechaini = utilitylib.objFechaToStr(sdate)
                fechafin = utilitylib.objFechaToStr(edate)

                sql ='''
                    DELETE FROM leulit_actividad_base WHERE fecha >= '{0}'::DATE AND fecha <= '{1}'::DATE; 
                    DELETE FROM leulit_actividad_base_dia WHERE fecha >= '{0}'::DATE AND fecha <= '{1}'::DATE;  
                    delete from leulit_actividad_16bravo WHERE fecha >= '{0}'::DATE AND fecha <= '{1}'::DATE; 
                    delete from leulit_actividad_16bravo_dia WHERE fecha >= '{0}'::DATE AND fecha <= '{1}'::DATE; 
                '''.format(fechaini, fechafin)

                new_cr.execute(sql)
                #new_cr.commit()
                for i in range(delta.days + 1):
                    day = sdate + timedelta(days=i)                                
                    fecha = utilitylib.objFechaToStr(day)
                    _logger.error('16BTH -> day = %r, fecha = %r',day,fecha)    
                    '''
                    if day.date() > datetime.now().date():
                        _logger.error('16BTH -> START CRM MEETING = %r', fecha)     
                        try:           
                            self.env['crm.meeting'].updDataActividadFecha(fecha, context)
                        except Exception as e2:
                            _logger.error('16BTH -> crm.meeting -> updDataActividadFecha ERROR --> %r',str(e2))  
                            raise UserError(e2)
                        new_cr.commit()
                    
                    _logger.error('16BTH -> START PARTE ESCUELA FECHA = %r', fecha)     
                    self.env['leulit.parte_escuela'].updDataActividadFecha(fecha)
                    new_cr.commit()
                    
                    _logger.error('16BTH -> START TAREA TIEMPO = %r', fecha)     
                    self.env['leulit.tarea_tiempo'].updDataActividadFecha(fecha)
                    new_cr.commit()
                    _logger.error('16BTH -> START PILOTO TAREA = %r', fecha)     
                    self.env['leulit.piloto.tarea'].updDataActividadFecha(fecha)
                    new_cr.commit()

                    _logger.error('16BTH -> START TALLER TAREA = %r', fecha)     
                    self.env['leulit.taller.tarea'].updDataActividadFecha(fecha)
                    new_cr.commit()
                    '''

                    _logger.error('16BTH -> START VUELOS FECHA = %r', fecha)    
                    self.env['leulit.vuelo'].updDataActividadFecha(fecha)
                    new_cr.commit()
                    #new_cr.close()
            except Exception as e:
                _logger.error('16BTH -> do_data_calculation ERROR --> %r',str(e))            
                new_cr.rollback()
                #new_cr.close()
                raise UserError(e)
            finally:
                _logger.error('16BTH -> do_data_calculation FINALLY')                            