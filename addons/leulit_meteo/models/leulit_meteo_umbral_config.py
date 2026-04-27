# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LeulitMeteoUmbralConfig(models.TransientModel):
    _name = 'leulit.meteo.umbral.config'
    _description = 'Umbrales Operacionales Meteorología'

    # Parámetros en ir.config_parameter
    PARAM_VIENTO_MARGINAL = 'leulit_meteo.umbral_viento_marginal_kt'
    PARAM_VIENTO_NOGO = 'leulit_meteo.umbral_viento_nogo_kt'
    PARAM_RACHAS_MARGINAL = 'leulit_meteo.umbral_rachas_marginal_kt'
    PARAM_RACHAS_NOGO = 'leulit_meteo.umbral_rachas_nogo_kt'
    PARAM_VIS_MARGINAL = 'leulit_meteo.umbral_vis_marginal_m'
    PARAM_VIS_NOGO = 'leulit_meteo.umbral_vis_nogo_m'

    # Viento sostenido
    viento_marginal_kt = fields.Integer(
        string='Viento marginal (kt)',
        default=20,
        help='Viento sostenido por encima del cual el estado pasa a MARGINAL.')
    viento_nogo_kt = fields.Integer(
        string='Viento NOGO (kt)',
        default=30,
        help='Viento sostenido por encima del cual el estado pasa a NO GO.')

    # Rachas
    rachas_marginal_kt = fields.Integer(
        string='Rachas marginales (kt)',
        default=30,
        help='Rachas por encima del cual el estado pasa a MARGINAL.')
    rachas_nogo_kt = fields.Integer(
        string='Rachas NOGO (kt)',
        default=40,
        help='Rachas por encima del cual el estado pasa a NO GO.')

    # Visibilidad
    vis_marginal_m = fields.Integer(
        string='Visibilidad marginal (m)',
        default=3000,
        help='Visibilidad por debajo de la cual el estado pasa a MARGINAL.')
    vis_nogo_m = fields.Integer(
        string='Visibilidad NOGO (m)',
        default=1500,
        help='Visibilidad por debajo de la cual el estado pasa a NO GO.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        res['viento_marginal_kt'] = int(ICP.get_param(self.PARAM_VIENTO_MARGINAL, 20))
        res['viento_nogo_kt'] = int(ICP.get_param(self.PARAM_VIENTO_NOGO, 30))
        res['rachas_marginal_kt'] = int(ICP.get_param(self.PARAM_RACHAS_MARGINAL, 30))
        res['rachas_nogo_kt'] = int(ICP.get_param(self.PARAM_RACHAS_NOGO, 40))
        res['vis_marginal_m'] = int(ICP.get_param(self.PARAM_VIS_MARGINAL, 3000))
        res['vis_nogo_m'] = int(ICP.get_param(self.PARAM_VIS_NOGO, 1500))
        return res

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param(self.PARAM_VIENTO_MARGINAL, self.viento_marginal_kt)
        ICP.set_param(self.PARAM_VIENTO_NOGO, self.viento_nogo_kt)
        ICP.set_param(self.PARAM_RACHAS_MARGINAL, self.rachas_marginal_kt)
        ICP.set_param(self.PARAM_RACHAS_NOGO, self.rachas_nogo_kt)
        ICP.set_param(self.PARAM_VIS_MARGINAL, self.vis_marginal_m)
        ICP.set_param(self.PARAM_VIS_NOGO, self.vis_nogo_m)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Guardado'),
                'message': _('Umbrales operacionales guardados.'),
                'type': 'success',
                'sticky': False,
            },
        }

    @classmethod
    def get_umbrales(cls, env):
        """Devuelve los umbrales activos como dict. Usar desde _compute_estado_meteo."""
        ICP = env['ir.config_parameter'].sudo()
        return {
            'viento_marginal': int(ICP.get_param(cls.PARAM_VIENTO_MARGINAL, 20)),
            'viento_nogo': int(ICP.get_param(cls.PARAM_VIENTO_NOGO, 30)),
            'rachas_marginal': int(ICP.get_param(cls.PARAM_RACHAS_MARGINAL, 30)),
            'rachas_nogo': int(ICP.get_param(cls.PARAM_RACHAS_NOGO, 40)),
            'vis_marginal': int(ICP.get_param(cls.PARAM_VIS_MARGINAL, 3000)),
            'vis_nogo': int(ICP.get_param(cls.PARAM_VIS_NOGO, 1500)),
        }
