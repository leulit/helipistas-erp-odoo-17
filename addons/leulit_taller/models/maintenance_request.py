# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from datetime import datetime
import pytz
import logging
import io
import re
import base64
from PyPDF2 import PdfFileWriter, PdfFileReader
from odoo.addons.web.controllers.main import Binary

_logger = logging.getLogger(__name__)

class MaintenanceRequest(models.Model):
    _name = "maintenance.request"
    _inherit = "maintenance.request"


    def _get_default_project(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('leulit.maintenance_hours_project'))


    @api.onchange('fecha_aceptacion','equipment_id')
    def onchange_aceptacion(self):
        if self.fecha_aceptacion:
            date_utc = self.fecha_aceptacion.astimezone(pytz.timezone('Europe/Madrid')).replace(tzinfo=None)
            horometro = self.equipment_id.get_tsn_to_date(date_utc)
            self.horometro = horometro


    def write(self, vals):
        res = super(MaintenanceRequest, self).write(vals)
        if 'stage_id' in vals:
            fecha_cierre = fields.Date.today()
            crs_incompletos = self.crs.filtered(lambda crs: crs.tipo_crs == 'incompleto')
            if crs_incompletos:
                fecha_cierre = max(crs_incompletos, key=lambda crs: crs.fecha).fecha
            self.filtered(lambda m: m.stage_id.done).write({'close_date': fecha_cierre})
        return res


    @api.onchange('stage_id')
    def onchange_stage(self):
        if self.stage_id:
            if self.accepted:
                if not self._origin.accepted:
                    self.fecha_aceptacion = datetime.now()
                self.helicoptero.statemachine = "En taller"
                self.horometro = self.helicoptero.airtime
            if self.flight:
                if self.checklist_tss:
                    self.env['leulit.tarea_sensible_seguridad'].comprobar_estado_wo_tss(self.id)
                else:
                    raise UserError('No ha rellenado las Tareas Sensibles para la Seguridad.')
                self.helicoptero.statemachine = "En servicio"
            if not self.accepted:
                self.fecha_aceptacion = False
                self.helicoptero.statemachine = "En servicio"
            if self.done:
                self._origin.comprobar_estado_wo()


    def _get_material(self):
        for request in self:
            request.material_ids = False
            self.env.companies = self.env['res.company'].search([('name','in',['Icarus Manteniment S.L.','Helipistas S.L.'])])
            request.material_ids = self.env['stock.move.line'].search([('maintenance_request_id','=',self.id),('state','=','done')])


    def _get_componentes(self):
        for request in self:
            request.componentes_ids = False
            self.env.companies = self.env['res.company'].search([('name','in',['Icarus Manteniment S.L.','Helipistas S.L.'])])
            request.componentes_ids = self.env['stock.move.line'].search([('maintenance_request_id','=',self.id),('state','=','done'),('is_rotable','=',True)])


    def _get_tasks_ids(self):
        for item in self:
            t_planificada = self.env['project.task'].search([('maintenance_request_id','=',item.id),('maintenance_planned_activity_id','!=',False),('parent_id','=',False)])
            internal_task = self.env['project.task'].search([('maintenance_request_id','=',item.id),('maintenance_planned_activity_id','=',False),('parent_id','=',False)])
            t_interna = self.env['project.task'].search([('maintenance_request_id','=',item.id),('tipo_tarea_taller','=','defecto_encontrado'),('parent_id','=',False)])
            t_sb = self.env['project.task'].search([('maintenance_request_id','=',item.id),('tipo_tarea_taller','=','service_bulletin'),('parent_id','=',False)])
            t_ad = self.env['project.task'].search([('maintenance_request_id','=',item.id),('tipo_tarea_taller','=','airworthiness_directive'),('parent_id','=',False)])
            item.task_planned_ids = t_planificada
            item.task_internal_ids = t_interna
            item.task_sb_ids = t_sb   
            item.task_ad_ids = t_ad   
            item.task_ids = t_planificada + internal_task + t_interna + t_sb + t_ad


    @api.onchange('checklist_tss')
    def onchange_checklist_tss(self):
        if self.checklist_tss:
            if self.tareas_sensibles_seguridad_ids:
                for item in self.tareas_sensibles_seguridad_ids:
                    item.unlink()
            for item in self.checklist_tss.tareas:
                item.copy(default={'checklist_id': False,'request_id':self.id})
        else:
            if self.tareas_sensibles_seguridad_ids:
                for item in self.tareas_sensibles_seguridad_ids:
                    item.unlink()


    @api.returns('self')
    def _default_stage(self):
        return self.env['maintenance.stage'].search([], limit=1)


    project_id = fields.Many2one(comodel_name="project.project", string="Proyecto", default=_get_default_project)
    task_ids = fields.One2many(compute=_get_tasks_ids, comodel_name="project.task", string="Tareas")
    task_internal_ids = fields.One2many(compute=_get_tasks_ids, comodel_name="project.task", string="Tareas internas")
    task_planned_ids = fields.One2many(compute=_get_tasks_ids, comodel_name="project.task", string="Tareas planificadas")
    task_sb_ids = fields.One2many(compute=_get_tasks_ids, comodel_name="project.task", string="Tareas Service Bulletin")
    task_ad_ids = fields.One2many(compute=_get_tasks_ids, comodel_name="project.task", string="Tareas Airworthiness Directive")
    helicoptero = fields.Many2one(related="equipment_id.helicoptero", string="Helicóptero")
    fabricante = fields.Selection(related="equipment_id.helicoptero.fabricante", string="Fabricante")
    modelo = fields.Many2one(related="equipment_id.helicoptero.modelo", string="Modelo")
    serialnum = fields.Char(related="equipment_id.helicoptero.serialnum", string="Número de serie")
    tsn = fields.Float(related="equipment_id.airtime_helicopter", string="TSN")
    tso = fields.Float(string="TSO")
    horometro = fields.Float(string="Horómetro")
    location = fields.Char(string="Lugar de la Inspección", default="LEUL")
    fecha_aceptacion = fields.Datetime(string="Fecha aceptación")
    emisor_ot = fields.Many2one(comodel_name="res.users", string="Emisor OT")
    accepted = fields.Boolean(related='stage_id.accepted')
    flight = fields.Boolean(related='stage_id.flight')
    done = fields.Boolean(related='stage_id.done')
    crs = fields.One2many(comodel_name="leulit.maintenance_crs", inverse_name="request", string="CRS")
    material_ids = fields.One2many(compute=_get_material, comodel_name="stock.move.line", string="Material")
    componentes_ids = fields.One2many(compute=_get_componentes, comodel_name="stock.move.line", string="Componentes")
    form_one_ids = fields.One2many(comodel_name="leulit.maintenance_form_one", inverse_name="work_order_id", string="Forms One")
    tareas_sensibles_seguridad_ids = fields.One2many(comodel_name="leulit.tarea_sensible_seguridad", inverse_name="request_id", string="Tareas Sensibles de Seguridad")
    checklist_tss = fields.Many2one(comodel_name="leulit.checklist_tareas_sensibles_seguridad", string="Plantilla de Tareas")
    expediente_mantenimiento = fields.Binary()
    combined_pdf_filename = fields.Char()
    lot_id = fields.Many2one(comodel_name="stock.lot", string="S/N")
    boroscopia_ids = fields.One2many(comodel_name="leulit.maintenance_boroscopia", inverse_name="request", string="Boroscopias")
    validated = fields.Boolean(default=False)
    encoded_pdf = fields.Binary()
    filename = fields.Char()
    referencia_programa_mantenimiento = fields.Char(string="Ref. Programa Mantenimiento")
    stage_id = fields.Many2one('maintenance.stage', string='Stage', ondelete='restrict', tracking=False,
                               group_expand='_read_group_stage_ids', default=_default_stage, copy=False)
    overhaul_tasks = fields.Boolean(string="Contiene tareas de revisión mayor")
    sale_order_id = fields.Many2one(comodel_name="sale.order", string="Presupuesto de venta")

    def open_sale_order(self):
        if self.sale_order_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Presupuesto de venta',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': self.sale_order_id.id,
                'target': 'current',
            }
        else:
            raise UserError('No hay presupuesto de venta asociado a esta Orden de Trabajo.')

    def create_sale_order_from_material_utilizado(self):
        company_icarus = self.env['res.company'].search([('name','=','Icarus Manteniment S.L.')])
        if not self.sale_order_id:
            if not self.equipment_id.owner:
                raise UserError('No se puede crear un presupuesto de venta porque el equipamiento no tiene propietario.')
            self.sale_order_id = self.env['sale.order'].create({
                'partner_id': self.equipment_id.owner.id,
                'date_order': datetime.now(),
                'company_id': company_icarus.id,
            })
            for material in self.material_ids:
                if 'DES' not in material.reference:
                    if material.lot_id.product_id:
                        self.env['sale.order.line'].create({
                            'order_id': self.sale_order_id.id,
                            'product_id': material.lot_id.product_id.id,
                            'name': material.lot_id.product_id.name,
                            'product_uom_qty': material.qty_done,
                            'price_unit': material.lot_id.precio * 1.2 
                        })

    def comprobar_estado_wo(self):
        if not self.env['project.task'].comprobar_estado_wo_tareas(self.id):
            raise UserError('No puede cerrar esta Orden de Trabajo porque tiene una/s tarea/s pendiente.')
        self.env['leulit.maintenance_crs'].comprobar_estado_wo_crs(self.id)
        self.env['leulit.maintenance_form_one'].comprobar_estado_wo_form_one(self.id)
        self.env['leulit.maintenance_boroscopia'].comprobar_estado_wo_boroscopia(self.id)
        if self.checklist_tss:
            self.env['leulit.tarea_sensible_seguridad'].comprobar_estado_wo_tss(self.id)
        else:
            raise UserError('No ha rellenado las Tareas Sensibles para la Seguridad.')


    def comprobacion_estados_crs(self):
        if not self.env['project.task'].comprobar_estado_wo_tareas(self.id):
            raise UserError('No puede crear un CRS porque tiene una/s tarea/s pendiente.')
        for tss in self.tareas_sensibles_seguridad_ids:
            if not tss.no_aplica:
                if not tss.check or not tss.d_check:
                    raise UserError('No puede crear un CRS porque tiene una/s tarea/s sensible para la seguridad sin chequear.')
        for crs in self.crs:
            if crs.estado != 'firmado':
                raise UserError("Los CRS anteriores deben estar firmados.")


    def validate_order_by_camo(self):
        for task in self.task_planned_ids:
            if task.stage_id.name == 'Realizada':
                horometro = self.horometro
                fecha = self.close_date
                if self.crs:
                    for crs in self.crs:
                        if crs.tipo_crs == 'incompleto':
                            horometro = crs.horas_crs
                            fecha = crs.fecha
                if task.maintenance_planned_activity_id.horas_last_done != 0:
                    task.maintenance_planned_activity_id.horas_last_done = horometro
                if task.maintenance_planned_activity_id.fecha_last_done:
                    task.maintenance_planned_activity_id.fecha_last_done = fecha
        self.validated = True


    def action_create_boroscopia(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20240212_1600_form')
        view_id = view_ref and view_ref[1] or False
        
        mecanico = self.env['leulit.mecanico'].search([('partner_id','=',self.env.user.partner_id.id),('active','=',True)])
        
        context = {
            'default_request': self.id,
            'default_fecha': datetime.now().date(),
            'default_mecanico': mecanico.id if mecanico else False,
            'default_tsn': self.horometro,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Boroscopia',
            'res_model': 'leulit.maintenance_boroscopia',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }


    def action_create_form_one(self):
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230706_1118_form')
        view_id = view_ref and view_ref[1] or False
        
        mecanico = self.env['leulit.mecanico'].search([('partner_id','=',self.env.user.partner_id.id),('active','=',True)])
        form_one_today = self.env['leulit.maintenance_form_one'].search([('fecha','=',datetime.now().date())])
        sequence = 1
        if len(form_one_today) > 0:
            sequence = len(form_one_today)+1
        name = 'ICM-'+datetime.now().strftime("%y%m%d")+'-'+str(sequence)

        context = {
            'default_tracking_number' : name,
            'default_work_order_id': self.id,
            'default_fecha': datetime.now().date(),
            'default_certificador': mecanico.id if mecanico else False,
            'default_remarks': '<br/>All aplicable AD and SB complied with',
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Form One',
            'res_model': 'leulit.maintenance_form_one',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }
    

    def action_create_maintenance_crs_incompleto(self):
        self.comprobacion_estados_crs()
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230623_1633_form')
        view_id = view_ref and view_ref[1] or False
        text = ''
        cont = 0
        for item in self.env['project.task'].search([('maintenance_request_id','=',self.id),('parent_id','=',False)], order="id asc").filtered(lambda l: l.stage_id.name == 'Realizada'):
            if cont == 0:
                text += '<b>TAREAS</b>'
            text += '<br/>'
            if item.tipo_tarea_taller != 'tarea':
                if item.tipo_tarea_taller == 'defecto_encontrado':
                    text += '- ' + re.sub(r'<[^>]*?>', '', item.solucion_defecto)
                if item.tipo_tarea_taller == 'service_bulletin' or item.tipo_tarea_taller == 'airworthiness_directive':
                    text += '- ' + re.sub(r'<[^>]*?>', '', item.name)
                for manual in item.manuales_ids:
                    text += ' ('
                    if manual.name:
                        text += ' Name:<b>' + manual.name + '</b>'
                    if manual.descripcion:
                        text += ' <b>' +  manual.descripcion + '</b>'
                    if manual.pn:
                        text += ' PN:<b>' +  manual.pn + '</b>'
                    if manual.rev_n:
                        text += ' Rev nº:<b>' +  manual.rev_n + '</b>'
                    if manual.rev:
                        text += ' Rev date:<b>' +  manual.rev.strftime('%d/%m/%Y') + '</b>'
                    text += ')'
                    break
            else:
                if item.maintenance_planned_activity_id:
                    referencia = item.maintenance_planned_activity_id.tarea_preventiva_id.referencia if item.maintenance_planned_activity_id.tarea_preventiva_id.referencia else ''
                    text += '- ' + item.maintenance_planned_activity_id.descripcion + ' (<b>' + referencia + '</b>)'
                else:
                    text += '- ' + re.sub(r'<[^>]*?>', '', item.name)
                    for manual in item.manuales_ids:
                        text += ' ('
                        if manual.name:
                            text += ' <b>Name:' + manual.name + '</b>'
                        if manual.descripcion:
                            text += ' <b>' +  manual.descripcion + '</b>'
                        if manual.pn:
                            text += ' <b>PN:' +  manual.pn + '</b>'
                        if manual.rev_n:
                            text += ' <b>Rev nº:' +  manual.rev_n + '</b>'
                        if manual.rev:
                            text += ' <b>Rev date:' +  manual.rev.strftime('%d/%m/%Y') + '</b>'
                        text += ')'
                        break

            cont += 1
        cont = 0
        for item in self.anomalia_ids:
            if cont == 0:
                if text != '':
                    text += '<br/><br/>'
                text += '<b>ANOMALIAS</b>'
            text += '<br/>'
            text += '- ' + item.discrepancia + ' (' + item.codigo + ')'
            cont += 1

        # ##########   SUSTITUCIÓN DE COMPONENTES   ##########
        if self.componentes_ids:
            if text != '':
                text += '<br/><br/>'
            text += '<b>Sustitución de Componentes</b>'
        for move_line in self.componentes_ids.filtered(lambda m: m.reference.startswith('INS')):
            off_move = move_line.move_line_component_contrary_id
            text += '<br/>'
            text += '<b>- OFF - P/N </b>' + off_move.product_id.default_code + '<b> - S/N </b>' + off_move.lot_id.sn + '<b> - Descripción </b>' + off_move.product_id.name + \
                    '<b> - TSN </b>' + str(off_move.lot_id.tsn_actual) + '<b> - TSO </b>' + str(off_move.lot_id.tso_actual) + '<b> - Realizado por </b>' + off_move.create_uid.name
            text += '<br/>'
            text += '<b>- ON - P/N </b>' + move_line.product_id.default_code + '<b> - S/N </b>' + move_line.lot_id.sn + '<b> - Descripción </b>' + move_line.product_id.name + \
                    '<b> - TSN </b>' + str(move_line.lot_id.tsn_actual) + '<b> - TSO </b>' + str(move_line.lot_id.tso_actual) + '<b> - Realizado por </b>' + move_line.create_uid.name
            text += '<br/>'

        mecanico = self.env['leulit.mecanico'].search([('partner_id','=',self.env.user.partner_id.id),('active','=',True),('certificador','=',True)])
        motor = self.equipment_id.get_motor()
        tso = 0
        if self.category_id:
            if self.category_id.name == 'Helicóptero':
                tso = self.equipment_id.helicoptero.tso
        context = {
            'default_tareas': text,
            'default_request': self.id,
            'default_horas_crs': self.horometro,
            'default_tso_crs': str(tso),
            'default_tsn_motor': motor.production_lot.tsn_actual if motor else 0,
            'default_tso_motor': str(motor.production_lot.tso_actual) if motor else 0,
            'default_certificador': mecanico.id if mecanico else False,
            'default_tipo_crs': 'incompleto',
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRS',
            'res_model': 'leulit.maintenance_crs',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }

    def action_create_maintenance_crs_completo(self):
        self.comprobacion_estados_crs()
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20230623_1633_form')
        view_id = view_ref and view_ref[1] or False
        text = ''
        crs_anterior_name = ''
        for item in self.env['leulit.maintenance_crs'].search([('request','=',self.id),('tipo_crs','=','incompleto')], limit=1, order="id desc"):
            if item.limitaciones:
                limitacion_anterior = item.limitaciones.name.replace('pending','permformed')
                if item.limitaciones.manual_id:
                    manual = item.limitaciones.manual_id
                    text += '- ' + limitacion_anterior + ' (' 
                    if manual.name:
                        text += ' Name:<b>' + manual.name + '</b>'
                    if manual.descripcion:
                        text += ' <b>' +  manual.descripcion + '</b>'
                    if manual.pn:
                        text += ' PN:<b>' +  manual.pn + '</b>'
                    if manual.rev_n:
                        text += ' Rev nº:<b>' +  manual.rev_n + '</b>'
                    if manual.rev:
                        text += ' Rev date:<b>' +  manual.rev.strftime('%d/%m/%Y') + '</b>'
                    text += ')<br/>'
                else:
                    text += '- ' + limitacion_anterior + '<br/>'
            crs_anterior_name = item.n_cas
        text += 'All other works of WO '+self.name+' already certified with CRS '+crs_anterior_name+' .'
        mecanico = self.env['leulit.mecanico'].search([('partner_id','=',self.env.user.partner_id.id),('active','=',True),('certificador','=',True)])
        motor = self.equipment_id.get_motor()
        tso = 0
        if self.category_id:
            if self.category_id.name == 'Helicóptero':
                tso = self.equipment_id.helicoptero.tso
        context = {
            'default_tareas': text,
            'default_request': self.id,
            'default_horas_crs': self.tsn,
            'default_tso_crs': str(tso),
            'default_tsn_motor': motor.production_lot.tsn_actual if motor else 0,
            'default_tso_motor': str(motor.production_lot.tso_actual) if motor else 0,
            'default_certificador': mecanico.id if mecanico else False,
            'default_tipo_crs': 'completo',
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRS',
            'res_model': 'leulit.maintenance_crs',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }
    
    def action_open_tasks(self):
        action_id = self.env.ref('leulit_taller.leulit_20230313_1500_action').read()[0]
        if self.task_ids:
            action_id['domain'] = [('id', 'in', self.task_ids.ids)]
        return action_id

    def action_create_internal_task(self):
        tags = self.env['project.tags'].search([('name', '=', 'Tareas de mantenimiento')])
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20250724_1244_form')
        view_id = view_ref and view_ref[1] or False
        context={
            'default_maintenance_request_id':self.id,
            'default_project_id': self.project_id.id,
            'default_maintenance_equipment_id': self.equipment_id.id,
            'default_tag_ids': tags.ids,
            'default_tipo_tarea_taller': 'tarea',
            'tracking_disable': True
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarea interna',
            'res_model': 'project.task',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }

    def action_create_defect_found(self):
        tags = self.env['project.tags'].search([('name', '=', 'Tareas de mantenimiento')])
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20250724_1244_form')
        view_id = view_ref and view_ref[1] or False
        context={
            'default_maintenance_request_id':self.id,
            'default_project_id': self.project_id.id,
            'default_maintenance_equipment_id': self.equipment_id.id,
            'default_tag_ids': tags.ids,
            'default_tipo_tarea_taller': 'defecto_encontrado',
            'tracking_disable': True
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Defecto encontrado',
            'res_model': 'project.task',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }

    def action_create_task_sb(self):
        tags = self.env['project.tags'].search([('name', '=', 'Tareas de mantenimiento')])
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20250724_1244_form')
        view_id = view_ref and view_ref[1] or False
        context={
            'default_maintenance_request_id':self.id,
            'default_project_id': self.project_id.id,
            'default_maintenance_equipment_id': self.equipment_id.id,
            'default_tag_ids': tags.ids,
            'default_tipo_tarea_taller': 'service_bulletin',
            'default_sb_ad_one_time': True,
            'tracking_disable': True
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarea Service Bulletin',
            'res_model': 'project.task',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }

    def action_create_task_ad(self):
        tags = self.env['project.tags'].search([('name', '=', 'Tareas de mantenimiento')])
        view_ref = self.env['ir.model.data'].get_object_reference('leulit_taller','leulit_20250724_1244_form')
        view_id = view_ref and view_ref[1] or False
        context={
            'default_maintenance_request_id':self.id,
            'default_project_id': self.project_id.id,
            'default_maintenance_equipment_id': self.equipment_id.id,
            'default_tag_ids': tags.ids,
            'default_tipo_tarea_taller': 'airworthiness_directive',
            'default_sb_ad_one_time': True,
            'tracking_disable': True
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarea Airworthiness directive',
            'res_model': 'project.task',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': context,
        }

    def action_view_timesheet_ids(self):
        action = super(MaintenanceRequest, self).action_view_timesheet_ids()
        action['context']["create"]=False
        return action

    def print_tareas_sensibles_seguridad(self):
        if self.checklist_tss:
            data = self._get_data_to_print_tareas_sensibles_seguridad()
            return self.env.ref('leulit_taller.leulit_20230927_1958_report').report_action(self, data=data)
        else:
            raise UserError('Debe seleccionar almenos la plantilla de Tareas Sensibles para la Seguridad.')

    def _get_data_to_print_tareas_sensibles_seguridad(self):
        data = {}
        tareas = []
        for task in self.env['leulit.tarea_sensible_seguridad'].search([('request_id','=',self.id)]):
            if task.no_aplica:
                tarea = {
                    'name' : task.name,
                    'check' : "N/A",
                    'd_check' : "N/A",
                }
            else:
                tarea = {
                    'name' : task.name,
                    'check' : task.user_check.name if task.user_check else "",
                    'd_check' : task.user_d_check.name if task.user_d_check else "",
                }
            tareas.append(tarea)
        data = {
            'n_exp' : 'EM'+self.name,
            'n_orden_trabajo' : self.name,
            'tareas_ctss' : tareas if len(tareas) != 0 else False,
        }
        return data


    def print_defectos(self):
        data = self._get_data_to_print_defectos()
        return self.env.ref('leulit_taller.leulit_20230926_1832_report').report_action(self, data=data)
    
    def _get_data_to_print_defectos(self):
        data = {}
        tareas = []
        for task in self.env['project.task'].search([('maintenance_request_id','=',self.id),('tipo_tarea_taller','=','defecto_encontrado')]):
            tarea = {
                'code' : task.code,
                'name' : task.solucion_defecto,
                'descripcion' : task.name,
                'asignado' : task.user_id.name,
                'fecha' : task.date_start,
                'doble_check_tecnico' : task.supervisado_por.name,
            }
            tareas.append(tarea)
        data = {
            'n_exp' : 'EM'+self.name,
            'n_orden_trabajo' : self.name,
            'tareas_defectos' : tareas if len(tareas) != 0 else False,
        }
        return data


    def print_inspeccion_seguridad(self):
        data = self._get_data_to_print_inspeccion_seguridad()
        return self.env.ref('leulit_taller.leulit_20230926_1322_report').report_action(self, data=data)

    def _get_data_to_print_inspeccion_seguridad(self):
        data = {}
        tareas = []
        for task in self.env['project.task'].search([('maintenance_request_id','=',self.id)], order="id asc"):
            for inspect in task.security_inspection_ids:
                tarea = {
                    'name' : inspect.name,
                    'primera_persona' : inspect.first_user_inspeccion_seguridad.name if inspect.first_user_inspeccion_seguridad else False,
                    'primera_fecha' : inspect.first_datetime_inspeccion_seguridad,
                    'segunda_persona' : inspect.second_user_inspeccion_seguridad.name if inspect.second_user_inspeccion_seguridad else False,
                    'segunda_fecha' : inspect.second_datetime_inspeccion_seguridad,
                }
                tareas.append(tarea)
        data = {
            'n_exp' : 'EM'+self.name,
            'n_orden_trabajo' : self.name,
            'tareas_is' : tareas if len(tareas) != 0 else False,
            'observaciones' : self.description
        }
        return data
    

    def print_doble_check(self):
        data = self._get_data_to_print_doble_check()
        return self.env.ref('leulit_taller.leulit_20230926_1711_report').report_action(self, data=data)
    

    def _get_data_to_print_doble_check(self):
        data = {}
        tareas = []
        cont = 1
        for task in self.env['project.task'].search([('maintenance_request_id','=',self.id)], order="id asc"):
            if task.doble_check_jb or task.doble_check_ata or task.doble_check_intern:
                for doble_check in task.double_check_ids:
                    tarea = {
                        'item' : cont,
                        'name' : doble_check.name,
                        'primera_persona' : doble_check.first_user_doble_check.name if doble_check.first_user_doble_check else False,
                        'primera_fecha' : doble_check.first_datetime_doble_check,
                        'segunda_persona' : doble_check.second_user_doble_check.name if doble_check.second_user_doble_check else False,
                        'segunda_fecha' : doble_check.second_datetime_doble_check,
                    }
                    tareas.append(tarea)
                    cont += 1
        data = {
            'n_exp' : 'EM'+self.name,
            'n_orden_trabajo' : self.name,
            'tareas_dc' : tareas if len(tareas) != 0 else False,
            'observaciones' : self.description
        }
        return data


    def print_material(self):
        self.env.companies = self.env['res.company'].search([('name','in',['Icarus Manteniment S.L.','Helipistas S.L.'])])
        items = self.env['stock.move.line'].search([('maintenance_request_id','=',self.id),('is_instalacion','=',True),('state','=','done')])
        data = self._get_data_to_print_material(items)
        pdf = self.env.ref('leulit_taller.leulit_20230118_1037_report')._render_qweb_pdf(self, data=data)[0]
        self.encoded_pdf = base64.b64encode(pdf)
        self.filename = "{0}.pdf".format('Material Utilizado'+self.name)

        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=maintenance.request&id=" + str(self.id) + "&filename_field=filename&field=encoded_pdf&download=true",
            'target': 'self'
        }

    def _get_data_to_print_material(self, items):
        data = {}
        materiales = []
        for item in items:
            precio_coste = 'N/A'
            try:
                if item.lot_id.lot_hlp_ica:
                    lot_hlp = item.lot_id.lot_hlp_ica
                    if lot_hlp.first_move.picking_id:
                        picking = lot_hlp.first_move.picking_id
                        if picking.purchase_id:
                            purchase = picking.purchase_id
                            for line in purchase.order_line:
                                if line.product_id.id == item.lot_id.product_id.id:
                                    precio_coste = line.price_unit
            except Exception as exc:
                pass

            material = {
                'name' : item.lot_id.product_id.name,
                'pn' : item.lot_id.product_id.default_code,
                'sn' : item.lot_id.sn if item.lot_id.sn else 'N/A',
                'revision' : item.lot_id.revision if item.lot_id.revision else 'N/A',
                'lote' : item.lot_id.lote if item.lot_id.lote else 'N/A',
                'ref_origen' : item.lot_id.ref_origen if item.lot_id.ref_origen else 'N/A',
                'qty' : item.qty_done,
                'price' : precio_coste,
                'empleado' : item.create_uid.name,
                'fecha' : item.date.strftime('%Y-%m-%d'),
            }
            materiales.append(material)
        
        items_per_page = 9
        total_items = len(materiales)
        remaining_items = items_per_page - (total_items % items_per_page) if total_items % items_per_page != 0 else 0
        
        empty_item = {
            'name': '-',
            'pn': '-',
            'sn': '-',
            'revision': '-',
            'lote': '-',
            'ref_origen': '-',
            'qty': '-',
            'price': '-',
            'empleado': '-',
            'fecha': '-'
        }
        
        materiales.extend([empty_item.copy() for _ in range(remaining_items)])
        pages = [materiales[i:i + items_per_page] for i in range(0, len(materiales), items_per_page)]

        data = {
            'n_exp' : 'EM'+self.name,
            'n_orden_trabajo' : self.name,
            'matricula' : self.equipment_id.helicoptero.name,
            'pages' : pages,
            'total_pages': len(pages),
            'observaciones' : self.description
        }

        return data
    

    def print_wo(self):
        data = self._get_data_work_order()
        pdf = self.env.ref('leulit_taller.leulit_20230905_1226_report')._render_qweb_pdf(self, data=data)[0]
        self.encoded_pdf = base64.b64encode(pdf)
        self.filename = "{0}.pdf".format(self.name)

        return {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=maintenance.request&id=" + str(self.id) + "&filename_field=filename&field=encoded_pdf&download=true",
            'target': 'self'
        }
    
    def _get_data_work_order(self):
        company_p145 = self.env['res.company'].search([('name','like','Icarus')])

        trabajos_realizar = {}
        if self.maintenance_plan_id:
            tags = []
            for task in self.task_planned_ids:
                if task.maintenance_planned_activity_id.int_h not in tags:
                    if task.maintenance_planned_activity_id.int_h > 0:
                        tags.append(task.maintenance_planned_activity_id.int_h)

            tags.sort()
            cont0 = 1
            # ##########   TRABAJOS A REALIZAR   ##########
            for tag in tags:
                cont = cont0 + 0.1
                lista_tareas = []
                for task in self.task_planned_ids.filtered(lambda t: t.maintenance_planned_activity_id.int_h == tag).sorted(key=lambda r: r.id):
                    lista = [round(cont,1), task.maintenance_planned_activity_id.descripcion, task.maintenance_planned_activity_id.tarea_preventiva_id.referencia, task.user_id.name if task.user_id and task.stage_id.name not in ['Pendiente','En proceso'] else '', task.supervisado_por.name if task.supervisado_por else '', True if task.stage_id.name == 'N/A' else False]
                    cont += 0.1
                    lista_tareas.append(lista)
                trabajos_realizar[int(tag)] = lista_tareas
                cont0 += 1
            lista_tareas = []
            for task in self.task_planned_ids.filtered(lambda t: t.maintenance_planned_activity_id.int_h == 0).sorted(key=lambda r: r.id):
                cont = cont0 + 0.1
                lista = [round(cont,1), task.maintenance_planned_activity_id.descripcion, task.maintenance_planned_activity_id.tarea_preventiva_id.referencia, task.user_id.name if task.user_id and task.stage_id.name not in ['Pendiente','En proceso'] else '', task.supervisado_por.name if task.supervisado_por else '', True if task.stage_id.name == 'N/A' else False]
                cont += 0.1
                lista_tareas.append(lista)
            if len(lista_tareas) > 0:
                trabajos_realizar['Others'] = lista_tareas
        else:
            cont0 = 1
            lista_tareas = []
            cont = cont0 + 0.1
            for task in self.env['project.task'].search([('maintenance_request_id','=',self.id),('maintenance_planned_activity_id','=',False),('parent_id','=',False),('tipo_tarea_taller','=','tarea')]):
                referencia_task = ''
                for manual in task.manuales_ids:
                    if manual.name:
                        referencia_task += '(' + manual.name + ')'
                    if manual.descripcion:
                        referencia_task += ' (' +  manual.descripcion + ')'
                    if manual.pn:
                        referencia_task += ' (' +  manual.pn + ')'
                    break
                lista = [round(cont,1), task.name, referencia_task, task.user_id.name if task.user_id and task.stage_id.name not in ['Pendiente','En proceso'] else '', task.supervisado_por.name if task.supervisado_por else '', True if task.stage_id.name == 'N/A' else False]
                cont += 0.1
                lista_tareas.append(lista)
            trabajos_realizar[''] = lista_tareas

        # ##########   ANOMALIAS   ##########
        anomalias = []
        cont_anomalias = 1
        for anomalia in self.anomalia_ids:
            anomalia = {
                'item' : cont_anomalias,
                'name' : anomalia.discrepancia,
                'referencia' : anomalia.codigo,
                'asignado' : anomalia.cerrado_por.name if anomalia.cerrado_por else '',
            }
            anomalias.append(anomalia)
            cont_anomalias += 1
        
        # ##########   SERVICE BULLETINS & DIRECTIVES   ##########
        service_bulletins = []
        cont_sb = 1
        for task in self.env['project.task'].search([('maintenance_request_id','=',self.id),('sb_ad_one_time','=',True)]):
            referencia = ''
            for manual in task.manuales_ids:
                if manual.name:
                    referencia += '(' + manual.name + ')'
                if manual.descripcion:
                    referencia += ' (' +  manual.descripcion + ')'
                if manual.pn:
                    referencia += ' (' +  manual.pn + ')'
                break
            tarea = {
                'item' : cont_sb,
                'name' : task.name,
                'referencia' : referencia,
                'asignado' : task.user_id.name,
            }
            service_bulletins.append(tarea)
            cont_sb += 1
        
        # ##########   SUSTITUCIÓN DE COMPONENTES   ##########
        moves_componentes = []
        for move_line in self.componentes_ids.filtered(lambda m: m.reference.startswith('INS')):
            off_move = move_line.move_line_component_contrary_id
            move_componente = {
                'off_pn' : off_move.product_id.default_code,
                'off_sn' : off_move.lot_id.sn,
                'off_descripcion' : off_move.product_id.name,
                'off_tsn' : off_move.lot_id.tsn_actual,
                'off_tso' : off_move.lot_id.tso_actual,
                'off_realizado_por' : off_move.create_uid.name,
                'on_pn' : move_line.product_id.default_code,
                'on_sn' : move_line.lot_id.sn,
                'on_descripcion' : move_line.product_id.name,
                'on_tsn' : move_line.lot_id.tsn_actual,
                'on_tso' : move_line.lot_id.tso_actual,
                'on_realizado_por' : move_line.create_uid.name,
            }
            moves_componentes.append(move_componente)

        motor = self.equipment_id.get_motor()
        responsable_mant = self.env['leulit.mecanico'].search([('active','=',True),('responsable_mant','=',True)])

        data={
            'plan_mantenimiento':self.maintenance_plan_id.name if self.maintenance_plan_id else self.referencia_programa_mantenimiento,
            'logo_hlp':self.company_id.logo_reports if self.company_id.name == 'Helipistas S.L.' else False,
            'logo_ica':self.company_id.logo_reports if self.company_id.name == 'Icarus Manteniment S.L.' else False,
            'name':self.name,
            'logo_p145':company_p145.logo_reports if company_p145.logo_reports else False,
            'name_user':self.create_uid.name,
            'fecha_emision':self.request_date,
            'fecha_aceptacion':self.fecha_aceptacion.date() if self.fecha_aceptacion else False,
            'matricula':self.equipment_id.helicoptero.name,
            'propietario_operador':self.equipment_id.owner.name if self.equipment_id and self.equipment_id.category_id.name == 'Helicóptero' else'Helipistas S.L.',
            'marca_aeronave':self.equipment_id.helicoptero.fabricante.capitalize() if self.equipment_id.helicoptero.fabricante else '',
            'modelo_aeronave':self.equipment_id.helicoptero.modelo.name,
            'sn_aeronave':self.equipment_id.helicoptero.serialnum,
            'tsn_aeronave':round(self.horometro,2),
            'tso_aeronave':round(self.equipment_id.helicoptero.tso,2) if round(self.equipment_id.helicoptero.tso,2)>0 else '-',
            'marca_motor':motor.marca_motor if motor else '-',
            'modelo_motor':motor.production_lot.product_id.default_code if motor else '-',
            'sn_motor':motor.production_lot.sn if motor else '-',
            'tsn_motor':round(motor.production_lot.tsn_actual,2) if motor and round(motor.production_lot.tsn_actual,2)>0 else '-',
            'tso_motor':round(motor.production_lot.tso_actual,2) if motor and round(motor.production_lot.tso_actual,2)>0 else '-',
            'ciclos_tsn':False,
            'ciclos_ng_tsn':False,
            'ciclos_nf_tsn':False,
            'ciclos_tso':False,
            'ciclos_ng_tso':False,
            'ciclos_nf_tso':False,
            'trabajos_realizar':trabajos_realizar,
            'anomalias' : anomalias if len(anomalias) != 0 else False,
            'service_bulletins' : service_bulletins if len(service_bulletins) != 0 else False,
            'moves_componentes' : moves_componentes if len(moves_componentes) != 0 else False,
            'responsable_mant':responsable_mant.name if responsable_mant else '',
            'create_hlp': True if self.company_id.name == 'Helipistas S.L.' else False,
            'create_icarus': True if self.company_id.name == 'Icarus Manteniment S.L.' else False,
            'observaciones' : self.description
            }
        return data
    
    def _get_data_to_print_log_cards_inspections(self):
        tareas = []
        for task in self.env['project.task'].search([('maintenance_request_id','=',self.id),('parent_id','=',False),('tipo_tarea_taller','!=','defecto_encontrado')], order="id asc"):
            subtareas = []
            for subtask in self.env['project.task'].search([('maintenance_request_id','=',self.id),('id','child_of',task.id), ('id', '!=', self.id)], order="id asc"):
                if subtask.subtask_count == 0:
                    subtarea = {
                        'name' : subtask.name,
                        'realizado_por' : subtask.user_id.name if subtask.stage_id.name not in ['Pendiente','En proceso'] else '',
                        'supervisado_por' : subtask.supervisado_por.name if subtask.stage_id.name not in ['Pendiente','En proceso'] and subtask.supervisado_por else ''
                    }
                    subtareas.append(subtarea)
            tarea = {
                'name' : task.name,
                'realizado_por' : task.user_id.name if task.stage_id.name not in ['Pendiente','En proceso'] else '',
                'supervisado_por' : task.supervisado_por.name if task.stage_id.name not in ['Pendiente','En proceso'] and task.supervisado_por else '',
                'subtareas' : subtareas if len(subtareas) != 0 else False
            }
            tareas.append(tarea)
        data = {
            'n_exp' : 'EM'+self.name,
            'n_orden_trabajo' : self.name,
            'all_tareas' : tareas if len(tareas) != 0 else False
        }
        return data
    

    def merge_pdfs(self, pdf_list):
        pdf_writer = PdfFileWriter()
        page_number = 1  # Inicializa el número de página

        for pdf_data in pdf_list:
            pdf_reader = PdfFileReader(io.BytesIO(pdf_data))
            for page_num in range(pdf_reader.getNumPages()):
                page = pdf_reader.getPage(page_num)
                pdf_writer.addPage(page)

        # Crear un objeto BytesIO para almacenar el PDF combinado en memoria
        combined_pdf = io.BytesIO()
        pdf_writer.write(combined_pdf)

        # Posiciona el puntero al inicio del archivo
        combined_pdf.seek(0)
        return combined_pdf


    def print_expediente_mantenimiento(self):
        """
        Genera el expediente de mantenimiento con mejor manejo de cabeceras
        """
        try:
            # Recopilar datos base
            data = {}
            data.update(self._get_data_work_order())
            data.update(self._get_data_to_print_defectos())
            data.update(self._get_data_to_print_log_cards_inspections())
            
            self.env.companies = self.env['res.company'].search([
                ('name', 'in', ['Icarus Manteniment S.L.', 'Helipistas S.L.'])
            ])
            
            items = self.env['stock.move.line'].search([
                ('maintenance_request_id', '=', self.id),
                ('is_instalacion', '=', True),
                ('state', '=', 'done')
            ])
            
            data.update(self._get_data_to_print_material(items))
            data.update(self._get_data_to_print_doble_check())
            data.update(self._get_data_to_print_inspeccion_seguridad())
            data.update(self._get_data_to_print_tareas_sensibles_seguridad())

            def calculate_content_size(tarea):
                """
                Calcula el espacio aproximado que ocupará una tarea en la página
                teniendo en cuenta el formato actual
                """
                # Espacio base para el título de la tarea
                size = 4  # Título + espaciado
                
                if tarea.get('subtareas'):
                    # Espacio para el encabezado de subtareas
                    size += 1
                    # Espacio para cada subtarea
                    size += len(tarea['subtareas'])
                    # Espacio adicional para separación
                    size += 1
                else:
                    # Espacio adicional para separación
                    size += 1

                return size

            def optimize_chunks(tareas, lines_per_page=40):
                """
                Optimiza la distribución de tareas en páginas para maximizar
                el uso del espacio disponible
                """
                chunks = []
                current_chunk = []
                current_lines = 0
                total_content_size = 0

                # Primero, calculamos el tamaño total del contenido
                for tarea in tareas:
                    total_content_size += calculate_content_size(tarea)

                # Calculamos el número óptimo de páginas
                optimal_pages = max(1, (total_content_size + lines_per_page - 1) // lines_per_page)
                target_size_per_page = total_content_size / optimal_pages

                for tarea in tareas:
                    tarea_size = calculate_content_size(tarea)
                    
                    # Si esta tarea haría que la página actual exceda significativamente
                    # el tamaño objetivo y ya tenemos contenido, comenzar nueva página
                    if (current_lines + tarea_size > target_size_per_page * 1.3 and 
                        current_chunk and 
                        len(chunks) < optimal_pages - 1):
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_lines = 0

                    current_chunk.append(tarea)
                    current_lines += tarea_size

                # Añadir el último chunk si existe
                if current_chunk:
                    chunks.append(current_chunk)

                # Ajustar los chunks si es necesario para equilibrar mejor el contenido
                balanced_chunks = balance_chunks(chunks, lines_per_page)
                
                return balanced_chunks

            def balance_chunks(chunks, lines_per_page):
                """
                Equilibra los chunks para que tengan un tamaño más uniforme
                """
                if len(chunks) <= 1:
                    return chunks

                # Calcular el tamaño de cada chunk
                chunk_sizes = []
                for chunk in chunks:
                    size = sum(calculate_content_size(tarea) for tarea in chunk)
                    chunk_sizes.append(size)
                return chunks

            # Modificar la función principal para usar estas nuevas funciones
            def generate_pdf_safely(report_ref, report_name, data_dict, is_continuation=False, chunk_index=None, total_chunks=None):
                try:
                    with api.Environment.manage():
                        with self.pool.cursor() as new_cr:
                            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                            report = new_env.ref(report_ref)
                            
                            local_data = dict(data_dict)
                            if is_continuation:
                                local_data.update({
                                    'is_continuation': True,
                                    'chunk_index': chunk_index,
                                    'total_chunks': total_chunks,
                                    'current_page': chunk_index + 1,
                                    'total_pages': total_chunks
                                })
                            
                            pdf_options = {
                                'margin-top': '25mm',
                                'margin-bottom': '20mm',
                                'margin-left': '15mm',
                                'margin-right': '15mm',
                                'encoding': 'utf-8',
                                'page-size': 'A4',
                                'dpi': '300',
                                '--header-spacing': '5',
                            }
                            
                            pdf = report.with_context(
                                force_report_rendering=True,
                                pdf_options=pdf_options
                            )._render_qweb_pdf(self.with_env(new_env), data=local_data)[0]
                            
                            return pdf
                except Exception as e:
                    _logger.error(f"Error generando {report_name}: {str(e)}")
                    return None

            # Lista de reportes con sus configuraciones específicas
            base_reports = [
                ('leulit_taller.leulit_20230905_1226_report', 'Orden de Trabajo'),
                ('leulit_taller.leulit_20230926_1832_report', 'Defectos'),
                ('leulit_taller.leulit_20231019_0745_report', 'Log Cards'),
                ('leulit_taller.leulit_20230118_1037_report', 'Material'),
                ('leulit_taller.leulit_20230926_1711_report', 'Doble Check'),
                ('leulit_taller.leulit_20230926_1322_report', 'Inspección Seguridad'),
                ('leulit_taller.leulit_20230927_1958_report', 'Tareas Sensibles'),
            ]

            pdf_list = []

            # Generar PDFs
            for report_ref, report_name in base_reports:
                # Verificar si necesitamos dividir el reporte en chunks
                if report_name == 'Log Cards':
                    all_tareas = data.get('all_tareas', [])
                    if all_tareas:
                        # Usar la nueva función de optimización
                        chunks = optimize_chunks(all_tareas, lines_per_page=40)
                        total_chunks = len(chunks)
                        
                        for i, chunk in enumerate(chunks):
                            chunk_data = dict(data)
                            chunk_data['all_tareas'] = chunk
                            pdf = generate_pdf_safely(
                                report_ref,
                                f"{report_name} - Parte {i + 1}", 
                                chunk_data,
                                True,
                                i,
                                total_chunks
                            )
                            if pdf:
                                pdf_list.append(pdf)
                    else:
                        pdf = generate_pdf_safely(report_ref, report_name, data)
                        if pdf:
                            pdf_list.append(pdf)

                elif report_name == 'Material':
                    # Mantener el chunking existente para Material
                    chunk_size = 8
                    materiales = data.get('materiales', [])
                    if len(materiales) > chunk_size:
                        total_chunks = (len(materiales) + chunk_size - 1) // chunk_size
                        for i in range(0, len(materiales), chunk_size):
                            chunk_data = dict(data)
                            chunk_data['materiales'] = materiales[i:i + chunk_size]
                            pdf = generate_pdf_safely(
                                report_ref, 
                                f"{report_name} - Parte {i//chunk_size + 1}", 
                                chunk_data, 
                                True, 
                                i//chunk_size,
                                total_chunks
                            )
                            if pdf:
                                pdf_list.append(pdf)
                    else:
                        pdf = generate_pdf_safely(report_ref, report_name, data)
                        if pdf:
                            pdf_list.append(pdf)
                else:
                    # Resto de reportes sin chunking
                    pdf = generate_pdf_safely(report_ref, report_name, data)
                    if pdf:
                        pdf_list.append(pdf)

            # Generar documentos adicionales
            if self.crs:
                for crs in self.crs:
                    docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_crs'),('idmodelo','=',crs.id)])
                    for doc in docs:
                        pdf_list.append(base64.b64decode(doc.datas))

            if self.form_one_ids:
                for form_one in self.form_one_ids:
                    docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_form_one'),('idmodelo','=',form_one.id)])
                    for doc in docs:
                        pdf_list.append(base64.b64decode(doc.datas))

            if self.boroscopia_ids:
                for boroscopia in self.boroscopia_ids:
                    docs = self.env['leulit_signaturedoc'].search([('modelo','=','leulit.maintenance_boroscopia'),('idmodelo','=',boroscopia.id)])
                    for doc in docs:
                        pdf_list.append(base64.b64decode(doc.datas))


            if not pdf_list:
                raise UserError('No se pudo generar ningún PDF del expediente')

            # Combinar PDFs y guardar
            try:
                combined_pdf = self.merge_pdfs(pdf_list)
                self.expediente_mantenimiento = base64.b64encode(combined_pdf.getvalue())
                self.combined_pdf_filename = f"Expediente de Mantenimiento {self.name}.pdf"
                
                self.env.cr.commit()

                return {
                    'type': 'ir.actions.act_url',
                    'url': f"web/content/?model=maintenance.request&id={self.id}"
                        f"&filename_field=combined_pdf_filename&field=expediente_mantenimiento&download=true",
                    'target': 'self'
                }
            except Exception as e:
                _logger.exception("Error al combinar PDFs")
                raise UserError(f"Error al generar el expediente completo: {str(e)}")
                
        except Exception as e:
            _logger.exception("Error general en print_expediente_mantenimiento")
            raise UserError(f"Error inesperado generando el expediente: {str(e)}")