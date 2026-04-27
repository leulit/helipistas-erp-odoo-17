# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _, sql_db
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime, date, timedelta
from odoo.addons.leulit import utilitylib
import threading

_logger = logging.getLogger(__name__)


class LeulitItemExperienciaMecanico(models.Model):
    _name = "leulit.item_experiencia_mecanico"
    _description = 'Registro de Experiencia de Mecánico'
    _order = 'date asc'


    date = fields.Date(string='Date')
    location = fields.Char(string='Location')
    ac_type = fields.Char(string='A/C or Type')
    ac_comp = fields.Char(string='A/C Rg. or Comp s/n')
    type_maintenance = fields.Selection(selection=[('A', 'A'), ('B', 'B'), ('C','C')], string="Type of maintenance")
    privilege = fields.Many2many(comodel_name="leulit.certificacion", relation="leulit_experiencia_certificacion" , column1="item_experiencia_id" , column2="certificacion_id", string="Privilege used")
    tipos_actividad_ids = fields.Many2many('leulit.tipo_actividad_mecanico','rel_item_experiencia_planned_activity','item_experiencia_id','tipo_actividad_id','Tipo actividad')
    ata_ids = fields.Many2many('leulit.ata','rel_item_experiencia_ata','item_experiencia_id','ata_id','ATAs')
    operation_performed = fields.Char(string='Operation performed')
    duration = fields.Float(string='Time Duration')
    maintenance_request_id = fields.Many2one(comodel_name='maintenance.request', string='Maintenance record ref.')
    remarks = fields.Html(string='Remarks')
    mecanico_id = fields.Many2one(comodel_name='leulit.mecanico', string='Mecánico')
    account_analytic_line_id = fields.Many2one('account.analytic.line', string='Account Analytic Line')

    def get_activity_to_report(self, actividad):
        for actividad_mecanico in self.tipos_actividad_ids:
            if actividad_mecanico.nombre == actividad:
                return 'X'
        return ''

    def get_duration_to_report(self):
        if self.duration:
            return utilitylib.leulit_float_time_to_str(self.duration)
        return ''
    
    def get_privilege_to_report(self):
        return ', '.join(priv.name for priv in self.privilege)

    def get_data_to_report(self):
        activity_flags = {
            'FOT': False,
            'SGH': False,
            'R/I': False,
            'TS': False,
            'MOD': False,
            'REP': False,
            'INSP': False,
            'Training': False,
            'Perform': False,
            'Supervise': False,
            'CRS': False,
        }

        for actividad in self.tipos_actividad_ids:
            if actividad.nombre in activity_flags:
                activity_flags[actividad.nombre] = True
        items = []
        for ata in self.ata_ids:
            item = {
                'date': self.date.strftime('%d/%m/%Y') if self.date else '',
                'location': self.location,
                'ac_type': self.ac_type,
                'ac_comp': self.ac_comp,
                'type_maintenance': self.type_maintenance,
                'privilege': ', '.join(priv.name for priv in self.privilege),
                'fot': 'X' if activity_flags['FOT'] else '',
                'sgh': 'X' if activity_flags['SGH'] else '',
                'ri': 'X' if activity_flags['R/I'] else '',
                'ts': 'X' if activity_flags['TS'] else '',
                'mod': 'X' if activity_flags['MOD'] else '',
                'rep': 'X' if activity_flags['REP'] else '',
                'insp': 'X' if activity_flags['INSP'] else '',
                'training': 'X' if activity_flags['Training'] else '',
                'perform': 'X' if activity_flags['Perform'] else '',
                'supervise': 'X' if activity_flags['Supervise'] else '',
                'crs': 'X' if activity_flags['CRS'] else '',
                'ata_ids': ata.ata_number.replace('ATA ', ''),
                'operation_performed': self.operation_performed,
                'duration': utilitylib.leulit_float_time_to_str(self.duration),
                'maintenance_record_ref': self.maintenance_request_id.name,
                'remarks': self.remarks,
            }
            items.append(item)

        return items
    

    def upd_acc_analytic_line_requests(self):
        _logger.error("upd_acc_analytic_line_requests ")
        threaded_calculation = threading.Thread(target=self.run_upd_acc_analytic_line_requests, args=([]))
        _logger.error("############################################# upd_acc_analytic_line_requests start thread")
        threaded_calculation.start()
        return {}
    

    def run_upd_acc_analytic_line_requests(self):
        new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        try:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            project_id = int(env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))

            for tarea in env['project.task'].search([('maintenance_request_id','!=',False)]):
                if tarea.timesheet_ids:
                    for aal in tarea.timesheet_ids:
                        aal.write({'maintenance_request_id': tarea.maintenance_request_id.id, 
                                   'project_id': project_id,
                                   'date_time':tarea.finish_date,
                                   'date_time_end': tarea.finish_date + timedelta(hours=0.5),
                                   'unit_amount': 0.5})
                        if tarea.item_job_card_id:
                            aal.write({'date_time_end': tarea.finish_date + timedelta(hours=tarea.item_job_card_id.tiempo_defecto),
                                       'unit_amount': tarea.item_job_card_id.tiempo_defecto})
            new_cr.commit()
        finally:
            new_cr.close()
        _logger.error("############################################# upd_acc_analytic_line_requests fin")


    def upd_datos_actividad(self, fecha_origen, fecha_fin):
        _logger.error("upd_datos_actividad ")
        threaded_calculation = threading.Thread(target=self.run_upd_datos_actividad, args=([fecha_origen,fecha_fin]))
        _logger.error("upd_datos_actividad start thread")
        threaded_calculation.start()
        return {}

    def run_upd_datos_actividad(self, fecha_origen, fecha_fin):
        new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        try:
            env = api.Environment(new_cr, self.env.uid, self.env.context)
            project_id = int(env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))

            domains = [
                [('project_id','=',project_id),('task_id','!=',False),('maintenance_request_id','!=',False),('date_time','>=',(datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d"))],
            ]
            if fecha_origen and fecha_fin:
                domains = [
                    [('project_id','=',project_id),('task_id','!=',False),('maintenance_request_id','!=',False),('date_time','>=',fecha_origen),('date_time','<=',fecha_fin)]
                ]
            for domain in domains:
                for aal in env['account.analytic.line'].search(domain, order="date_time ASC"):
                    mecanico = env['leulit.mecanico'].search([('user_id','=',aal.user_id.id)])
                    mecanico_supervisor = False
                    if aal.task_id.parent_id.supervisado_por:
                        mecanico_supervisor = aal.task_id.parent_id.supervisado_por
                        actividades = env['leulit.tipo_actividad_mecanico'].search([('id','in',aal.task_id.tipos_actividad.ids)])
                        actividades_supervisor = env['leulit.tipo_actividad_mecanico'].search([('nombre','in',['Supervise','CRS'])])
                        tipos_actividad_supervisor = actividades + actividades_supervisor
                    maint_request = aal.with_context(lang='es_ES').maintenance_request_id
                    if mecanico:
                        item_experiencia = env['leulit.item_experiencia_mecanico'].search([('mecanico_id','=',mecanico.id),('account_analytic_line_id','=',aal.id)])
                        ac_type = ''
                        ac_comp = ''
                        certifications_ids = []
                        certifications_with_model = False
                        helicoptero = False
                        if maint_request.equipment_id:
                            if maint_request.equipment_id.helicoptero:
                                helicoptero = maint_request.equipment_id.helicoptero
                            else:
                                if maint_request.equipment_id.first_parent:
                                    helicoptero = maint_request.equipment_id.first_parent.helicoptero

                            if maint_request.equipment_id.category_id.id == 1:
                                ac_type = helicoptero.fabricante.capitalize()
                                ac_comp = maint_request.equipment_id.name
                            else:
                                ac_type = maint_request.equipment_id.production_lot.product_id.default_code
                                ac_comp = maint_request.equipment_id.production_lot.sn

                        else:
                            if maint_request.lot_id:
                                ubi_destino = env['stock.location'].search([('name','=','Equipamiento')])
                                ubi_origen = env['stock.location'].search([('name','=','Material Pendiente Decisión')])
                                last_uninstall = env['stock.move.line'].search([('lot_id','=',maint_request.lot_id.id),('location_dest_id','=',ubi_destino.id), ('location_id','=',ubi_origen.id)],order="date ASC", limit=1)
                                if last_uninstall.maintenance_request_id:
                                    if last_uninstall.equipment:
                                        helicoptero = last_uninstall.equipment.helicoptero
                                ac_type = maint_request.lot_id.product_id.default_code
                                ac_comp = maint_request.lot_id.production_lot.sn

                        if helicoptero and hasattr(helicoptero, 'fabricante'):
                            if helicoptero.fabricante == 'guimbal':
                                certifications_with_model = env['leulit.certificacion_aeronave'].search([('aeronave','=','cabri_g2'),('id','in',mecanico.certificaciones_ids.ids)])
                            if helicoptero.fabricante == 'robinson':
                                certifications_with_model = env['leulit.certificacion_aeronave'].search([('aeronave','=','r22_r44'),('id','in',mecanico.certificaciones_ids.ids)])
                            if helicoptero.fabricante == 'eurocopter':
                                certifications_with_model = env['leulit.certificacion_aeronave'].search([('aeronave','=','ec_120'),('id','in',mecanico.certificaciones_ids.ids)])
                        if certifications_with_model:
                            for certification in certifications_with_model:
                                if certification.certificacion_id.id in aal.task_id.certificacion_ids.ids:
                                    certifications_ids.append(certification.certificacion_id.id)
                        if not certifications_ids:
                            certifications_ids = env['leulit.certificacion'].search([('name','=','B1')]).ids

                        if not item_experiencia:
                            env['leulit.item_experiencia_mecanico'].create({
                                'mecanico_id': mecanico.id,
                                'date': aal.date_time,
                                'location': maint_request.location,
                                'ac_type': ac_type,
                                'ac_comp': ac_comp,
                                'type_maintenance': aal.task_id.type_maintenance,
                                'privilege': certifications_ids,
                                'tipos_actividad_ids': aal.task_id.tipos_actividad,
                                'ata_ids': aal.task_id.ata_ids,
                                'operation_performed': aal.task_id.solucion_defecto if aal.task_id.tipo_tarea_taller == 'defecto_encontrado' else aal.task_id.name,
                                'duration': aal.unit_amount,
                                'maintenance_request_id': aal.maintenance_request_id.id,
                                'account_analytic_line_id': aal.id,
                                'remarks': aal.task_id.description,
                            })
                        else:
                            item_experiencia.write({
                                'mecanico_id': mecanico.id,
                                'date': aal.date_time,
                                'location': maint_request.location,
                                'ac_type': ac_type,
                                'ac_comp': ac_comp,
                                'type_maintenance': aal.task_id.type_maintenance,
                                'privilege': certifications_ids,
                                'tipos_actividad_ids': aal.task_id.tipos_actividad,
                                'ata_ids': aal.task_id.ata_ids,
                                'operation_performed': aal.task_id.solucion_defecto if aal.task_id.tipo_tarea_taller == 'defecto_encontrado' else aal.task_id.name,
                                'duration': aal.unit_amount,
                                'maintenance_request_id': aal.maintenance_request_id.id,
                                'account_analytic_line_id': aal.id,
                                'remarks': aal.task_id.description,
                            })

                        if mecanico_supervisor:
                            item_experiencia_supervisor = env['leulit.item_experiencia_mecanico'].search([('mecanico_id','=',mecanico_supervisor.id),('account_analytic_line_id','=',aal.id)])

                            if not item_experiencia_supervisor:
                                env['leulit.item_experiencia_mecanico'].create({
                                    'mecanico_id': mecanico_supervisor.id,
                                    'date': aal.date_time,
                                    'location': maint_request.location,
                                    'ac_type': ac_type,
                                    'ac_comp': ac_comp,
                                    'type_maintenance': aal.task_id.type_maintenance,
                                    'privilege': certifications_ids,
                                    'tipos_actividad_ids': tipos_actividad_supervisor,
                                    'ata_ids': aal.task_id.ata_ids,
                                    'operation_performed': aal.task_id.solucion_defecto if aal.task_id.tipo_tarea_taller == 'defecto_encontrado' else aal.task_id.name,
                                    'duration': aal.unit_amount,
                                    'maintenance_request_id': aal.maintenance_request_id.id,
                                    'account_analytic_line_id': aal.id,
                                    'remarks': aal.task_id.description,
                                })
                            else:
                                item_experiencia_supervisor.write({
                                    'mecanico_id': mecanico_supervisor.id,
                                    'date': aal.date_time,
                                    'location': maint_request.location,
                                    'ac_type': ac_type,
                                    'ac_comp': ac_comp,
                                    'type_maintenance': aal.task_id.type_maintenance,
                                    'privilege': certifications_ids,
                                    'tipos_actividad_ids': tipos_actividad_supervisor,
                                    'ata_ids': aal.task_id.ata_ids,
                                    'operation_performed': aal.task_id.solucion_defecto if aal.task_id.tipo_tarea_taller == 'defecto_encontrado' else aal.task_id.name,
                                    'duration': aal.unit_amount,
                                    'maintenance_request_id': aal.maintenance_request_id.id,
                                    'account_analytic_line_id': aal.id,
                                    'remarks': aal.task_id.description,
                                })

            new_cr.commit()
        finally:
            new_cr.close()
        _logger.error("run_upd_datos_actividad fin")
