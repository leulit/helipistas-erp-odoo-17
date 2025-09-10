# -*- encoding: utf-8 -*-
from odoo.addons.leulit import utilitylib
from odoo import models, fields, api, _
import logging
from datetime import timedelta
import threading
_logger = logging.getLogger(__name__)

from datetime import datetime, date, timedelta


class leulitAnomaliaScripts(models.Model):
    _name           = "leulit.anomalia_scripts"
    _description    = "leulit_anomalia_scripts"


    def firmar_cerrar_anomalia(self,idanomalia):
        _logger.error("################### firmar_cerrar_anomalia ")
        threaded_calculation = threading.Thread(target=self.run_firmar_cerrar_anomalia, args=([idanomalia]))
        _logger.error("################### firmar_cerrar_anomalia start thread")
        threaded_calculation.start()

    def run_firmar_cerrar_anomalia(self,idanomalia):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            context = dict(self._context)
            anomalias = self.env['leulit.anomalia'].with_context(context).sudo().search([('id','=',idanomalia)])
            for anomalia in anomalias:
                args={'otp':'654321',
                      'notp':'654321',
                      'modelo':'leulit.anomalia',
                      'idmodelo':anomalia.id}
                context['args']=args
                self.env.uid = 14
                if anomalia.cerrado_por:
                    user = self.env['res.users'].with_context(context).sudo().search([('partner_id','=',anomalia.cerrado_por.id)])
                    self.env.uid = user.id
                self.env['leulit_signaturedoc'].with_context(context).sudo().checksignatureRef()
                self.env.cr.commit()
        _logger.error('################### firmar_cerrar_anomalia fin thread')