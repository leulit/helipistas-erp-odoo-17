# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class LeulitMeteoParams(models.TransientModel):
    _name = 'leulit.meteo.params'
    _description = 'Parámetros Meteorología'

    PARAM_EMAIL_ERRORES = 'leulit_meteo.email_errores'

    email_errores = fields.Char(
        string='Email(s) para notificación de errores',
        help='Dirección(es) de correo separadas por coma. '
             'Se enviarán avisos cuando la actualización automática de METAR '
             'encuentre errores. Si se deja vacío no se enviarán notificaciones.')

    cron_activo = fields.Boolean(
        string='Actualización automática de METAR activa',
        help='Activa o desactiva la tarea programada que descarga METAR/TAF '
             'para todos los aeródromos de referencia cada 2 horas.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        res['email_errores'] = ICP.get_param(self.PARAM_EMAIL_ERRORES, '')
        cron = self.env.ref(
            'leulit_meteo.cron_actualizar_metar_referencia',
            raise_if_not_found=False)
        res['cron_activo'] = bool(cron and cron.active)
        return res

    def action_sincronizar_icao_espana(self):
        """Delega la sincronización de aeródromos de referencia en el modelo correspondiente."""
        return self.env['leulit.meteo.icao.reference'].action_sincronizar_desde_checkwx()

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param(self.PARAM_EMAIL_ERRORES, self.email_errores or '')
        cron = self.env.ref(
            'leulit_meteo.cron_actualizar_metar_referencia',
            raise_if_not_found=False)
        if cron:
            cron.sudo().write({'active': self.cron_activo})
        return {'type': 'ir.actions.act_window_close'}
