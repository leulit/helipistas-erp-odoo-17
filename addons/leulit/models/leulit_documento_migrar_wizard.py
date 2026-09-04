# -*- encoding: utf-8 -*-
from odoo import models, fields


class LeulitDocumentoMigrarWizard(models.TransientModel):
    """
    Asistente para lanzar a mano, desde el propio ERP, la migración de los
    mecanismos de documentación antiguos (alumno/piloto/mecánico) al modelo
    unificado leulit.documento. Ver leulit.documento.migrar_documentos_legacy().
    """
    _name = "leulit.documento_migrar_wizard"
    _description = "leulit_documento_migrar_wizard"

    resumen = fields.Text(string="Resultado", readonly=True)

    def action_migrar(self):
        self.ensure_one()
        resumen = self.env['leulit.documento'].migrar_documentos_legacy()
        self.resumen = '\n'.join(resumen) if resumen else 'No había nada que migrar.'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Migrar documentos antiguos',
            'res_model': 'leulit.documento_migrar_wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
