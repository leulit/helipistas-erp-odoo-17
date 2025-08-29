# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


_actividades = []

class leulit_actividad_base_dia(models.Model):
    _name = "leulit.actividad_base_dia"
    _description = "leulit_actividad_base_dia"
    _order = "fecha desc, inicio asc, partner"

    _max_duration = 11.0    
    planificada = False
    actividades = []


    def getTiempoFacturableMesYear(self, partner_id, month, year):
        startFecha = "{0}-{1}-01".format(int(year), int(month))
        datos = utilitylib.getStartEndMonth( strfecha = startFecha )
        endFecha = datos['endmonth']
        objs_abd = self.search([('partner','=',partner_id), ('fecha','>=',startFecha), ('fecha','<=',endFecha), ('prevista','=',False)])       
        total = 0
        for item in objs_abd:
            total = total + item.tiempo_facturable
        return total


    def getTiempoFacturableYear(self, partner_id, year):
        startFecha = "{0}-01-01".format(int(year))
        endFecha = "{0}-12-31".format(int(year))
        objs_abd = self.search([('partner','=',partner_id), ('fecha','>=',startFecha), ('fecha','<=',endFecha), ('prevista','=',False)])       
        total = 0
        for item in objs_abd:
            total = total + item.tiempo_facturable
        return total


    def delPrevData(self, fecha, partner):        
        if (partner):
            sql = """
                DELETE FROM leulit_actividad_base_dia
                WHERE 
                        fecha = '{0}'::DATE 
                    AND
                        partner = {1}
                    AND
                        prevista = 't'
            """.format(fecha, partner)
            self._cr.execute(sql)

    def readActividades(self, fecha, partner):
        if (partner):
            sql1 = """
                SELECT 
                    * 
                FROM 
                    leulit_actividad_base 
                WHERE 
                    fecha = '{0}'::DATE 
                AND partner = {1}
                ORDER BY
                    inicio ASC
            """.format(fecha, partner)  
            _actividades = utilitylib.runQuery(self._cr, sql1)                  
                


    def getId(self, fecha, partner):
        self.readActividades(fecha, partner)
        if len(_actividades) > 0:
            item = self.search([('partner','=', partner), ('fecha','=',fecha)])
            if len(item) > 0:
                return item
            else:
                return self.create({'partner': partner, 'fecha': fecha})
        return None

    def updateIdInActividades(self, fecha, partner, iditem):
        if (partner):
            sql = """
                UPDATE
                    leulit_actividad_base
                SET
                    actividad_base_dia_id = {0}
                WHERE 
                    fecha = '{1}'::DATE
                AND
                    partner = {2}
            """.format(iditem, fecha, partner) 
            self._cr.execute( sql )
    

    def calcTiempo(self, datos):
        result = {            
            'tiempo' : 0.0,
            'valid_activity_time' : 'N.A.',
        }        
        if _actividades and len(_actividades) > 0:
            for actividad in _actividades:
                result['tiempo'] = round(float(result['tiempo']),2) + round(float(actividad.tiempo_calc_laboral),2)
        result['valid_activity_time'] = "green" if round(float(result['tiempo']),2) <= round(float(self._max_duration),2) else "red"
        return result

    def doCalculations(self, item16B):
        item16B['inicio'] = round(float(item16B['inicio_calc']),2)
        item16B['fin'] = round(float(item16B['fin_calc']),2)
        datos16b = {
            'inicio'                : item16B['inicio'],
            'fin'                   : item16B['fin'],
            'tiempo'                : round(float(item16B['fin']),2) - round(float(item16B['inicio']),2),
            'dias_trabajados_mes'   : item16B['dias_trabajados_mes_calc'],
            'dias_trabajados_year'  : item16B['dias_trabajados_year_calc'],
            'dias_planif_mes'       : item16B['dias_planif_mes_calc'],
            'dias_planif_year'      : item16B['dias_planif_year_calc'],
        }
        result = self.calcTiempo(datos16b)
        datos16b.update(result)
        self.write(item16B['id'], datos16b)
        return datos16b

    def deleteCeroActividades(self):
        items = self.search([('actividades','=',False)])
        items.unlink()


    def updateData(self, fecha, partner):
        self.delPrevData(fecha, partner)
        item = self.getId(fecha, partner)
        result = None
        if item:
            self.updateIdInActividades(fecha, partner, item.id)
            result = self.doCalculations(item16B)
        else:
            if (partner):
                sql = """
                    DELETE FROM leulit_actividad_base_dia WHERE fecha = '{0}'::DATE AND partner = {1}
                """.format(fecha, partner)
                self._cr.execute(sql)                
        self.deleteCeroActividades()
        return result


    def _calc_facturable(self, fecha, user):
        self.readActividades(fecha, user)
        intervals = []
        for actividad in _actividades:
            intervals.append([actividad['inicio'], actividad['fin']])
        #['tiempo'] = round(float(result['tiempo']),2) + round(float(actividad['tiempo_calc_laboral']),2)        
        intervals.sort(key=lambda x: x[0])
        merged = []
        for interval in intervals:
            # if the list of merged intervals is empty or if the current
            # interval does not overlap with the previous, simply append it.
            if not merged or merged[-1][1] < interval[0]:
                merged.append(interval)
            else:
            # otherwise, there is overlap, so we merge the current and previous
            # intervals.
                merged[-1][1] = max(merged[-1][1], interval[1])
        
        result = 0
        for interval in merged:
            result = result + (interval[1] - interval[0])
        return result


    def _tiempo_facturable(self):       
        res = {}
        for item in self:  
            sql = "SELECT sum(tiempo_calc_laboral) AS total FROM  leulit_actividad_base WHERE partner = {0} AND fecha = '{1}'::DATE AND prevista='f'".format(item.partner.id,item.fecha)
            row = utilitylib.runQueryReturnOne(self._cr, sql)        
            total = 0
            if row:
                total = row['total'] if row['total'] else 0.0
            if utilitylib.str_date_less(item['fecha'], "2020-12-31"):
                sql = '''
                    SELECT * FROM leulit_actividad_base_rutas
                    WHERE
                        fecha = '{0}'::DATE
                        AND
                        user_id = {1}
                '''.format(item.fecha,item.partner.id)
                row = utilitylib.runQueryReturnOne(self._cr, sql)
                if row:
                    if row['ruta_clh'] > 0:
                        total = total if total <= 10.0 else 10.0                       
                    elif row['ruta_enagas'] > 0:
                        total = total if total <= 10.0 else 10.0               
                    elif row['ruta_gas_natural'] > 0:
                        total = total if total <= 8.0 else 8.0                       
                    elif row['ruta_aguas'] > 0:
                        total = total if total <= 8.0 else 8.0                       
                    elif row['guardia_bomberos'] > 0:
                        total = total if total <= 11.0 else 11.0                       
                    else:
                        #total = total if total <= 8.0 else 8.0
                        valor = self._calc_facturable(item.fecha, item.partner.id)                        
                        total = total if total <= valor else valor
                        total = total if total <= 11 else 11
            else:
                #total = total if total <= 8.0 else 8.0
                total = total if total <= 8.0 else 8.0
            self.tiempo_facturable = total


          


    @api.depends('inicio','fin')
    def _tiempo(self):
        for item in self:
            item.tiempo = round(float(item.fin),2) - round(float(item.inicio),2)


    fecha = fields.Date('Fecha', select=1)
    prevista = fields.Boolean('Prevista')
    partner = fields.Many2one('res.partner', 'Usuario', ondelete='restrict', select=1)
    inicio = fields.Float('Inicio actividad', digits=(16, 2))
    fin = fields.Float('Fin actividad', digits=(16, 2))
    #tiempo = fields.Float("Tiempo actividad", digits=(16, 2))
    tiempo = fields.Float(compute=_tiempo, store=True, string="Tiempo actividad", digits=(16, 2))    
    dias_trabajados_mes = fields.Integer("Días trabajados mes")
    dias_planif_mes = fields.Integer("Días pendientes mes")
    dias_trabajados_year = fields.Integer("Días trabajados año")
    dias_planif_year = fields.Integer("Días pendientes año")
    actividades = fields.One2many('leulit.actividad_base', 'actividad_base_dia_id', 'Actividades')
    valid_activity_time = fields.Char(string='Tiempo actividad valido')
    tiempo_facturable = fields.Float(compute=_tiempo_facturable, store=True, digits=(16, 2))
    


    def detalle(self):
        return True
    # def detalle(self, ids, context=None):
    #     view_ref = self.pool.get('ir.model.data')._xmlid_to_res_model_res_id('leulit_actividad'. 'leulit_20201211_1750_tree')
    #     view_id = view_ref and view_ref[1] or False
    #     if context is None:
    #         context = {}
    #     itemIds = self.pool['actividad_base'].search([('actividad_base_dia_id','=',ids)])
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Detalle actividad día',
    #         'res_model': 'actividad_base',
    #         'view_type': 'form',
    #         'view_mode': 'tree',
    #         'view_id': view_id,
    #         'res_id': itemIds,
    #         'context': context,
    #         'initial_mode': 'view',
    #         'target': 'new',
    #         'domain': [('actividad_base_dia_id','in',ids)],
    #         'flags' : {'form': {'action_buttons': False}}
    #     }