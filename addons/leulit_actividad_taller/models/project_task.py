# Copyright 2019 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, api, models


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = "project.task"


    @api.onchange('item_job_card_id')
    def onchange_item_job_card(self):
        tag_id = self.env['project.tags'].search([('name','=','Tareas de mantenimiento')])
        if self.item_job_card_id:
            self.write({
                'maintenance_equipment_id' : self.item_job_card_id.equipamiento_id.id,
                'name' : self.item_job_card_id.descripcion,
                'production_lot_id' : self.item_job_card_id.equipamiento_id.production_lot.id,
                'type_maintenance' : self.item_job_card_id.type_maintenance,
                'ata_ids' : self.item_job_card_id.ata_ids.ids,
                'certificacion_ids' : self.item_job_card_id.certificacion_ids.ids,
                'manuales_ids' : self.item_job_card_id.manual_id.ids,
                'tag_ids': tag_id.ids,
                'tipos_actividad': self.item_job_card_id.tipos_actividad.ids
            })


    tipos_actividad = fields.Many2many('leulit.tipo_actividad_mecanico','rel_tipo_actividad_project_task','project_task_id','tipo_actividad_id','Tipo actividad mecánico')