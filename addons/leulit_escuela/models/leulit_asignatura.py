# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib

_logger = logging.getLogger(__name__)


class leulit_asignatura(models.Model):
    _name = "leulit.asignatura"
    _description    = "leulit_asignatura"
    _rec_name = "descripcion"
    _inherit = ['mail.thread']



    def _get_silabus_teoria(self):
        for item in self:
            item.silabus_teorico_ids = self.env['leulit.silabus'].search([('asignatura_id','=',item.id),('tipo','=','teorica')])

    #def _silabus_teorico_ids(self, cr, uid, ids, context=None):
    #    idsresult = []
    #    for item in self.pool.get('leulit.silabus').read(cr, uid, ids,['asignatura_id'],context):
    #        if item['asignatura_id'] not in idsresult:
    #            idsresult.append(item['asignatura_id'][0])
    #    return idsresult


    def _get_silabus_practica(self):
        for item in self:
            item.silabus_practico_ids = self.env['leulit.silabus'].search([('asignatura_id','=',item.id),('tipo','=','practica')])

    #def _silabus_practico_ids(self, cr, uid, ids, context=None):
    #    idsresult = []
    #    for item in self.pool.get('leulit.silabus').read(cr, uid, ids,['asignatura_id'],context):
    #        if item['asignatura_id'] not in idsresult:
    #            idsresult.append(item['asignatura_id'][0])
    #    return idsresult
    

    def _get_cursos(self):
        for item in self:
            idsSilabus = self.env['leulit.silabus'].search([('asignatura_id','=',item.id)])
            result = []
            for item2 in idsSilabus:
                if item2.curso_id and item2.curso_id.id not in result:
                    result.append(item2.curso_id.id)
            if result:
                item.curso_ids = result
            else:
                item.curso_ids = False


    #def _curso_ids(self, cr, uid, ids, context=None):
    #    idsresult = []
    #    for item in self.pool.get('leulit.silabus').read(cr, uid, ids,['asignatura_id'],context):
    #        if item['asignatura_id'] not in idsresult:
    #            idsresult.append(item['asignatura_id'][0])
    #    return idsresult

    @api.depends('curso_ids')
    def _get_num_cursos(self):
        for item in self:
            if item.curso_ids:
                item.num_cursos = len(item.curso_ids)
            else:
                item.num_cursos = 0
    
    @api.depends('silabus_ids')
    def _get_num_silabus(self):
       for item in self:
           item.num_silabus = len(item.silabus_ids)
    
    @api.model
    def _get_tiempo(self):
       for item in self:
           idssilabus = self.env['leulit.silabus'].search([('asignatura_id','=',item.id)])
           idsquery = []
           [idsquery.append(x.id) for x in idssilabus if x.id not in idsquery]
           idspartes = self.env['leulit.parte_escuela'].search([('silabus','in',idsquery)])
           item.tiempo = sum(o2m.tiempo for o2m in idspartes)


    def get_horasTeoricas_byCurso(self, idasignatura, idcurso):
       silabus = self.env['leulit.silabus'].search([('asignatura_id','=',idasignatura),('curso_id','=',idcurso)])
       total = 0
       for item in silabus:
           total = total + item.duracion
       return total

    @api.depends('silabus_teorico_ids')
    def _get_horas_teoria(self):
        for item in self:
            item.horas_teoria = sum(o2m.duracion for o2m in item.silabus_teorico_ids)


    @api.depends('silabus_practico_ids')
    def _get_horas_practica(self):
        for item in self:
            item.horas_practica = sum(o2m.duracion for o2m in item.silabus_practico_ids)

    
    descripcion = fields.Char('Descripción', required=True)
    curso_ids = fields.One2many(compute='_get_cursos', comodel_name="leulit.curso", string="Cursos", store=False)
    num_cursos = fields.Integer(compute='_get_num_cursos', string="Num. Cursos",store=False)
    silabus_ids = fields.One2many(comodel_name='leulit.silabus', inverse_name='asignatura_id', string='Silabus')
    num_silabus = fields.Integer(compute='_get_num_silabus', string="Num. Silabus",store=False)
    silabus_teorico_ids = fields.One2many(compute=_get_silabus_teoria, comodel_name="leulit.silabus", string="Silabus teórico", store=False)
    silabus_practico_ids = fields.One2many(compute=_get_silabus_practica, comodel_name="leulit.silabus", string="Silabus práctico", store=False)
    tiempo = fields.Float(compute=_get_tiempo, string="Horas impartidas", store=False)
    horas_teoria = fields.Float(compute='_get_horas_teoria', string="Horas teoría", store=False)
    horas_practica = fields.Float(compute='_get_horas_practica', string="Horas práctica", store=False)
    attachment_ids = fields.Many2many('ir.attachment', 'asignatura_attachment_rel', 'asignatura_id', 'attachment_id', string='Attachments')
    


