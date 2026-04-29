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
        return anotacion

    def unlink(self):
        if not self.env.user.has_group("leulit.RBase_hide"): 
            for item in self:
                if item.estado in ['closed','pending']:
                    raise UserError('Una anotación cerrada o pendiente no puede ser eliminada. Pongase en contacto con el responsable de operaciones.')
        return super(leulit_anotacion_technical_log, self).unlink()

    @api.onchange('fecha_cierre')
    def onchange_fecha_cierre(self):
        for item in self:
            item.fecha_crs = item.fecha_cierre

    def wizard_close(self):
        self.estado = "closed"
        self.cerrado_por = self.env.user.partner_id.id
        self.crs_por = self.env.user.partner_id.id
        self.wizard_send_email()

    def wizard_pending(self):
        self.estado = "pending"
        self.wizard_send_email()

    def wizard_edition(self):
        self.estado = "edition"

    def wizard_send_email(self):
        context = self.env.context.copy()
        if self.estado == "pending":
            context.update({'subject': u' Se pone en pendiente la anotación({0})'.format(self.codigo)})
        if self.estado == "closed":
            context.update({'subject': u' Se ha cerrado la anotación ({0})'.format(self.codigo)})
        template = self.with_context(context).env.ref("leulit_seguridad.leulit_anotacion_technical_log_mail_camo_estado")
        try:
            template.send_mail(self.id, force_send=True, raise_exception=True)
        except Exception as e:
            pass

    def _send_reminder_email(self):
        context = self.env.context.copy()
        context.update({'subject': u'Aviso: quedan 3 días para la fecha de la anotación ({0})'.format(self.codigo)})
        template = self.with_context(context).env.ref("leulit_seguridad.leulit_anotacion_technical_log_mail_camo_estado")
        try:
            template.send_mail(self.id, force_send=True, raise_exception=True)
        except Exception as e:
            _logger.error("Error enviando email de aviso para anotacion %s: %s", self.codigo, e)

    def edit_anotacion(self):
        self.ensure_one()
        view = self.env.ref('leulit_seguridad.leulit_20260401_1013_form',raise_if_not_found=False)        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Anotación',
            'res_model': 'leulit.anotacion_technical_log',
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': view.id if view else False,
            'target': 'current',
        }

    @api.model
    def _cron_check_anotacion_technical_log(self):
        today = fields.Date.today()
        fecha_aviso = today + timedelta(days=3)

        # Registros cuya fecha es exactamente dentro de 3 días → enviar email de aviso
        records_aviso = self.search([
            ('estado', '=', 'edition'),
            ('fecha', '=', fecha_aviso),
        ])
        for record in records_aviso:
            record._send_reminder_email()

        # Registros cuya fecha ya ha llegado → pasar a pendiente
        records_vencidos = self.search([
            ('estado', '=', 'edition'),
            ('fecha', '=', today),
        ])
        for record in records_vencidos:
            record.wizard_pending()

    codigo = fields.Char('Code', readonly=True)
    estado = fields.Selection([('edition', 'En edición'),('pending', 'Pendiente'),('closed', 'Cerrado')], 'State',default="edition")

    anotacion = fields.Text('Comment', required=True)
    fecha = fields.Date('Date', required=True)
    informado_por = fields.Many2one('res.partner', 'Reported by', readonly=True)
    rol_informa = fields.Selection([('1','Pilot'),('2','Mechanic'),('3','CAMO'),('4','Others')],'')
    lugar = fields.Char('Place')
    helicoptero_id = fields.Many2one('leulit.helicoptero', 'Helicopter', required=True, domain="[('baja','=',False)]")

    fecha_cierre = fields.Date('Closing date')
    cerrado_por = fields.Many2one('res.partner', 'Closed by', readonly=True)
    rol_close = fields.Selection([('1', 'Pilot'), ('2', 'Mechanic'),('3','CAMO'),('4','Others')], '')
    accion_cierre = fields.Text('Reason')

    fecha_crs = fields.Date('CRS date')
    crs_por = fields.Many2one('res.partner', 'CRS by', readonly=True)
    lugar_crs = fields.Char('Place')
    
    company_id =fields.Many2one('res.company', 'Company', default=1, readonly=True)
    logo = fields.Binary('Logo', related='company_id.logo_reports', readonly=True)

    maintenance_request_id = fields.Many2one(comodel_name="maintenance.request", string="Work Order")
    calendar_event_id = fields.Many2one(comodel_name="calendar.event", string="Planning event", ondelete="set null")

    is_operational = fields.Boolean('Operational', default=False)
    flight_id = fields.Many2one('leulit.vuelo', 'Flight')
    deadline_time = fields.Char('Deadline time (HH:MM)', default='12:00')

    install_dual_control = fields.Boolean('Dual control')
    install_cargo_hook_mirror = fields.Boolean('Cargo hook and mirror')
    install_floats = fields.Boolean('Floats')
    install_life_raft = fields.Boolean('Life raft')
    install_life_vests_qty = fields.Integer('Life vests qty')
    install_headsets_qty = fields.Integer('Headsets qty')
    install_tyler = fields.Boolean('Tyler')
    install_gss = fields.Boolean('GSS')
    install_cineflex = fields.Boolean('Cineflex')
    install_lidar_system = fields.Boolean('Lidar system')

    remove_dual_control = fields.Boolean('Dual control')
    remove_cargo_hook_mirror = fields.Boolean('Cargo hook and mirror')
    remove_floats = fields.Boolean('Floats')
    remove_life_raft = fields.Boolean('Life raft')
    remove_life_vests_qty = fields.Integer('Life vests qty')
    remove_headsets_qty = fields.Integer('Headsets qty')
    remove_tyler = fields.Boolean('Tyler')
    remove_gss = fields.Boolean('GSS')
    remove_cineflex = fields.Boolean('Cineflex')
    remove_lidar_system = fields.Boolean('Lidar system')

    def _get_operational_items(self, mode):
        items = []
        if mode == 'install':
            if self.install_floats:
                items.append('floats')
            if self.install_dual_control:
                items.append('dual control')
            if self.install_cargo_hook_mirror:
                items.append('cargo hook and mirror')
            if self.install_life_raft:
                items.append('life raft')
            if self.install_life_vests_qty > 0:
                items.append('{0} life vests'.format(self.install_life_vests_qty))
            if self.install_headsets_qty > 0:
                items.append('{0} headsets'.format(self.install_headsets_qty))
            if self.install_tyler:
                items.append('Tyler')
            if self.install_gss:
                items.append('GSS')
            if self.install_cineflex:
                items.append('Cineflex')
            if self.install_lidar_system:
                items.append('Lidar system')
        if mode == 'remove':
            if self.remove_floats:
                items.append('floats')
            if self.remove_dual_control:
                items.append('dual control')
            if self.remove_cargo_hook_mirror:
                items.append('cargo hook and mirror')
            if self.remove_life_raft:
                items.append('life raft')
            if self.remove_life_vests_qty > 0:
                items.append('{0} life vests'.format(self.remove_life_vests_qty))
            if self.remove_headsets_qty > 0:
                items.append('{0} headsets'.format(self.remove_headsets_qty))
            if self.remove_tyler:
                items.append('Tyler')
            if self.remove_gss:
                items.append('GSS')
            if self.remove_cineflex:
                items.append('Cineflex')
            if self.remove_lidar_system:
                items.append('Lidar system')
        return items

    def _build_operational_annotation(self):
        install_items = self._get_operational_items('install')
        remove_items = self._get_operational_items('remove')
        fecha_str = self.fecha.strftime('%d/%m/%Y') if self.fecha else 'DD/MM/YYYY'
        hora_str = self.deadline_time if self.deadline_time else 'HH:MM'

        clauses = []
        if install_items:
            clauses.append('{0} must be installed'.format(' / '.join(install_items)))
        if remove_items:
            clauses.append('{0} must be removed'.format(' / '.join(remove_items)))

        if self.flight_id and self.flight_id.codigo:
            reference_clause = 'before flight to {0}.'.format(self.flight_id.codigo)
        else:
            reference_clause = 'before day {0} at {1}.'.format(fecha_str, hora_str)

        if not clauses:
            return False

        actions = ', and '.join(clauses)
        return 'For operational reasons, {0}, {1}'.format(actions, reference_clause)

    @api.onchange(
        'is_operational', 'fecha', 'flight_id', 'deadline_time',
        'install_floats', 'install_dual_control', 'install_cargo_hook_mirror', 'install_life_raft',
        'install_life_vests_qty', 'install_headsets_qty',
        'install_tyler', 'install_gss', 'install_cineflex', 'install_lidar_system',
        'remove_floats', 'remove_dual_control', 'remove_cargo_hook_mirror', 'remove_life_raft',
        'remove_life_vests_qty', 'remove_headsets_qty',
        'remove_tyler', 'remove_gss', 'remove_cineflex', 'remove_lidar_system',
    )
    def _onchange_build_annotation(self):
        if not self.is_operational:
            return
        text = self._build_operational_annotation()
        if text:
            self.anotacion = text