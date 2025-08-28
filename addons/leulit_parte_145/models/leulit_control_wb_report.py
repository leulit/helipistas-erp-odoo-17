# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_informes_control_wb_report(models.Model):
    _name           = "leulit.informes_control_wb_report"
    _description    = "leulit_informes_control_wb_report"
    _auto           = False
    _order          = "modeloname"


    matricula = fields.Char('Matrícula', size=50, readonly=True)
    fechalastWB = fields.Date('Último informe peso y centrado',readonly=True)
    emptyweight = fields.Float('Peso vacío (kg.)', reaonly=True)
    longarm = fields.Float('CG. Long. cms.', reaonly=True)
    latarm = fields.Float('CG. Lat. kg/cm', reaonly=True)
    wblastmod = fields.Date('Fecha introducción de datos en ERP', reaonly=True)
    pesomax = fields.Float('Peso max. (kgs.)', reaonly=True)
    modeloname = fields.Char('Modelo', size=50, readonly=True)
    ctrlmantenimiento = fields.Boolean('Gestión mantenimiento')
    
    
    # def init(self):
    #     tools.drop_view_if_exists(self._cr, 'leulit_informes_control_wb_report')
    #     self._cr.execute("""
    #         CREATE OR REPLACE VIEW leulit_informes_control_wb_report AS (
    #             SELECT
    #             	a.id,
    #                 a.name as matricula,
    #                 a."fechalastWB",
    #                 a.emptyweight,
    #                 a.longarm,
    #                 a.latarm,
    #                 a.wblastmod,
    #                 a.ctrlmantenimiento,
    #                 leulit_modelohelicoptero.name as modeloname,
    #                 leulit_modelohelicoptero.pesomax as pesomax
    #             FROM 
    #                 leulit_helicoptero as a 
    #             INNER JOIN leulit_modelohelicoptero ON a.modelo = leulit_modelohelicoptero.id
    #        )""")
    