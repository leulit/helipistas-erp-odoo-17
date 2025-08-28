# -*- encoding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions, registry, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
from odoo.addons.leulit import utilitylib
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class leulit_checklist(models.Model):
    _name = "leulit.checklist"
    _description = "leulit_checklist"
    _rec_name = "descriptor"
    _order = "fecha_doit desc"
    _inherit = ['mail.thread']


    def checklist_print_report(self):
        for rec in self:
            items_checklist = []
            for item in rec.items:
                items_checklist.append({
                    'descriptor' : item.descriptor,
                    'orden' : item.orden,
                })
            data = {
                'items' : items_checklist,
                'descriptor':  rec.descriptor,
            }
            return self.env.ref('leulit.report_leulit_checklist').report_action([],data=data)


    def getTemplateValues(self, plantilla):
        checklistitems = []
        usuarios = []
        tags = []
        if plantilla:
            if plantilla.usuarios:
                for usuario in plantilla.usuarios:
                    usuarios.append(usuario.id)
            if plantilla.items:
                #checklistitems.append((5,))
                for item1 in plantilla.items:
                    checklistitems.append((0,0,{
                        'descriptor'    : item1.descriptor,
                        'orden'         : item1.orden
                    }))
            if plantilla.tags:
                for tag in plantilla.tags:
                    tags.append(tag.id)
        values = {
            'items'             : checklistitems,
            'usuarios'          : [(6, 0, usuarios)],
            'tags'              : [(6, 0, tags)],
            'descriptor'        : plantilla.descriptor,
            'tiempo_previsto'   : plantilla.tiempo_previsto,
        }
        return values
    

    @api.onchange('template')
    def onchange_template(self):
        value = self.getTemplateValues(self.template)
        self.items = False
        self.items = value['items']
        self.usuarios = value['usuarios']
        self.tags = value['tags']
        self.descriptor = value['descriptor']
        self.tiempo_previsto = value['tiempo_previsto']
        

    @api.model
    def create(self, vals):
        if 'template' in vals:
            template = self.env['leulit.checklist_template'].browse(vals['template'])
            tmpvalues = self.getTemplateValues(template)
            vals.update(tmpvalues)
        vals['realizado_por'] = self.env.uid
        
        result = super(leulit_checklist, self).create(vals)
        if result.template:
            attachment_to_copy = self.env['ir.attachment'].search([('res_model', '=', 'leulit.checklist_template'),('res_id', '=', result.template.id)])
            for attachment in attachment_to_copy:
                attachment.copy(default={'res_model': 'leulit.checklist','res_id':result.id})
        return result

    def write(self, vals):
        if 'template' in vals:
            template = self.env['leulit.checklist_template'].browse(vals['template'])
            tmpvalues = self.getTemplateValues(template)
            vals.update(tmpvalues)
        result = super(leulit_checklist, self).write(vals)
        attachment_to_remove = self.env['ir.attachment'].search([('res_model', '=', 'leulit.checklist'),('res_id', '=', self.id)])
        attachment_to_remove.unlink()
        if self.template:
            attachment_to_copy = self.env['ir.attachment'].search([('res_model', '=', 'leulit.checklist_template'),('res_id', '=', self.template.id)])
            for attachment in attachment_to_copy:
                attachment.copy(default={'res_model': 'leulit.checklist','res_id':self.id})
        return result


    def updFinalizado(self):
        finalizado = True
        for item1 in self.items:
            if not item1.doit:
                finalizado = False
                break
        if finalizado:
            self.finalizado = True


    def _tipo_get(self):
        idsItems = self.env['leulit.checklist_tag'].search([])
        res = [(item.id, item.descriptor) for item in idsItems]
        return res



    tags = fields.Many2many('leulit.checklist_tag', 'leulit_checklist_tag_rel', 'checklist_id','checklist_tag_id', 'Clasificación')
    descriptor = fields.Char("Descriptor", size=500, required=True)
    comentarios = fields.Text("Comentarios")
    template = fields.Many2one('leulit.checklist_template', 'Plantilla', required=True, domain=lambda self: "[('state','=','1'),('usuarios','in',"+str(self.env.uid)+")]")
    project_id = fields.Many2one(related='template.project_id', string='Proyecto')
    account_id = fields.Many2one(related='project_id.analytic_account_id', string='Cuenta analítica')
    company_id = fields.Many2one(related='project_id.company_id', string='Compañía')
    fecha_doit = fields.Date("Fecha realización",default=fields.Date.context_today)
    realizado_por = fields.Many2one('res.users', 'Autor')
    finalizado = fields.Boolean(string='Finalizado')
    items = fields.One2many('leulit.checklist_item','checklist_id','Items')
    usuarios = fields.Many2many('res.users','leulit_checklist_user_rel','checklist_id','user_id','Destinatarios')
    tipo = fields.Selection(_tipo_get, string='Tipo')
    tiempo_previsto = fields.Float(string="Tiempo previsto",readonly=True)