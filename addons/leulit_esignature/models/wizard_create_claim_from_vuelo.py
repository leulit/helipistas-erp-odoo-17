from datetime import datetime, timedelta
from this import d

from odoo import _, api, fields, models


class WizardCreateClaimFromVuelo(models.TransientModel):
    _name = "wizard_create_claim_from_vuelo"

    
    def guardar_ocurrencia_from_vuelo(self):
        name = 'Incidencia actividad aérea, el vuelo {0} sobrepasa la actividad aérea'.format(self.vuelo.codigo)
        self.env['mgmtsystem.claim'].create({'name':name,'partner_id': self.who.id,'description':self.descripcion})
        self.vuelo.write({'control_firma' : 'pendiente'})
        return {"type": "ir.actions.act_window_close"}
    
    def descartar_ocurrencia_from_vuelo(self):
        return {"type": "ir.actions.act_window_close"}


    descripcion = fields.Text('')
    who = fields.Many2one('res.partner','')
    vuelo = fields.Many2one('leulit.vuelo','')