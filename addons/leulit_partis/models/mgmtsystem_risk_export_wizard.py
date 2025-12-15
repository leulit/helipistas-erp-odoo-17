# -*- coding: utf-8 -*-
"""
Wizard para exportar análisis de riesgos a formato CSV.
Cumple con IS.D.OR.215 (Información de los activos) y IS.D.OR.305 (Mejora continua).
"""

import csv
import io
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MgmtsystemRiskExportWizard(models.TransientModel):
    _name = 'mgmtsystem.risk.export.wizard'
    _description = 'Exportar Análisis de Riesgos a CSV'

    asset_ids = fields.Many2many(
        'mgmtsystem.hazard',
        string='Activos',
        help='Filtrar por activos específicos (vacío = todos)'
    )
    threat_ids = fields.Many2many(
        'mgmtsystem.risk.threat',
        string='Amenazas',
        domain="[('magerit_threat_id', '!=', False)]",
        help='Filtrar por amenazas específicas (vacío = todas)'
    )
    include_treatment_plan = fields.Boolean(
        string='Incluir Plan de Tratamiento',
        default=True,
        help='Incluir columnas de estrategia, controles y estados de implementación'
    )
    only_high_critical = fields.Boolean(
        string='Solo Riesgos Altos/Críticos',
        help='Exportar únicamente riesgos con nivel residual 4-5'
    )
    file_data = fields.Binary(
        string='Archivo CSV',
        readonly=True
    )
    file_name = fields.Char(
        string='Nombre del Archivo',
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Configurar'),
        ('done', 'Exportado')
    ], default='draft', string='Estado')

    def action_export_csv(self):
        """Genera el archivo CSV con los análisis de riesgo filtrados."""
        self.ensure_one()

        # Construir dominio de búsqueda
        domain = [('magerit_threat_id', '!=', False)]
        
        if self.asset_ids:
            domain.append(('id', 'in', self.asset_ids.ids))
        
        if self.threat_ids:
            # Necesitamos buscar en mgmtsystem.risk, no en hazard
            # Cambiamos la estrategia
            pass
        
        if self.only_high_critical:
            domain.append(('residual_level', 'in', [4, 5]))

        # Obtener registros de activos
        hazards = self.env['mgmtsystem.hazard'].search(domain)
        
        if not hazards:
            raise UserError(_('No se encontraron registros que cumplan los criterios de filtrado.'))

        # Crear archivo CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Escribir encabezados
        headers = [
            'Código Activo',
            'Nombre Activo',
            'Tipo',
            'Ubicación',
            'Valoración (C)',
            'Valoración (I)',
            'Valoración (D)',
            'Nivel Activo',
            'Amenaza Código',
            'Amenaza',
            'Vulnerabilidad',
            'Probabilidad',
            'Impacto Potencial',
            'Nivel Inherente',
            'Controles Existentes',
            'Nivel Residual',
        ]
        
        if self.include_treatment_plan:
            headers.extend([
                'Estrategia',
                'Controles Propuestos',
                'Estado Plan',
                'Responsable',
                'Fecha Objetivo',
            ])
        
        writer.writerow(headers)

        # Escribir datos
        risks_exported = 0
        for hazard in hazards:
            # Filtrar por amenazas si se especificaron
            threat_domain = []
            if self.threat_ids:
                threat_domain.append(('magerit_threat_id', 'in', self.threat_ids.ids))
            
            # Buscar riesgos asociados
            risk_model = self.env['mgmtsystem.risk']
            risks = risk_model.search([
                ('hazard_id', '=', hazard.id),
                ('magerit_threat_id', '!=', False)
            ] + threat_domain)
            
            if self.only_high_critical:
                risks = risks.filtered(lambda r: r.residual_level in [4, 5])
            
            for risk in risks:
                row = [
                    hazard.asset_code or '',
                    hazard.name or '',
                    hazard.asset_type or '',
                    hazard.asset_location or '',
                    str(hazard.asset_value_c or 0),
                    str(hazard.asset_value_i or 0),
                    str(hazard.asset_value_d or 0),
                    str(hazard.asset_score or 0),
                    risk.magerit_threat_id.code or '',
                    risk.magerit_threat_id.name or '',
                    ', '.join(risk.vulnerability_ids.mapped('name')) or '',
                    str(risk.threat_probability or 0),
                    str(risk.potential_impact or 0),
                    str(risk.inherent_level or 0),
                    ', '.join(risk.existing_control_ids.mapped('name')) or '',
                    str(risk.residual_level or 0),
                ]
                
                if self.include_treatment_plan:
                    row.extend([
                        dict(risk._fields['strategy'].selection).get(risk.strategy, ''),
                        ', '.join(risk.proposed_control_ids.mapped('name')) or '',
                        dict(risk._fields['treatment_plan_state'].selection).get(risk.treatment_plan_state, ''),
                        risk.approver_id.name or '',
                        risk.target_date.strftime('%d/%m/%Y') if risk.target_date else '',
                    ])
                
                writer.writerow(row)
                risks_exported += 1

        if risks_exported == 0:
            raise UserError(_('No se encontraron riesgos que cumplan los criterios de filtrado.'))

        # Convertir a bytes y codificar en base64
        csv_data = output.getvalue()
        output.close()
        
        file_data = base64.b64encode(csv_data.encode('utf-8'))
        file_name = 'analisis_riesgos_{}.csv'.format(
            fields.Datetime.now().strftime('%Y%m%d_%H%M%S')
        )

        # Actualizar el wizard
        self.write({
            'file_data': file_data,
            'file_name': file_name,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_back(self):
        """Volver a la configuración inicial."""
        self.write({
            'file_data': False,
            'file_name': False,
            'state': 'draft',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
