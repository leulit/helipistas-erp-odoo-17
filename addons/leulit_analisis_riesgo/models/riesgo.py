from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import io
import xlsxwriter
from datetime import datetime


class AnalisisRiesgo(models.Model):
    """Modelo cabecera para agrupar análisis de riesgo"""
    _name = 'analisis.riesgo'
    _description = 'Análisis de Riesgo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Nombre del Análisis',
        required=True,
        tracking=True,
        help='Nombre descriptivo para este análisis de riesgo'
    )
    
    
    fecha_analisis = fields.Date(
        string='Fecha de Análisis',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
        help='Fecha en que se realizó el análisis'
    )
    
    responsable_principal = fields.Many2one(
        'res.users',
        string='Responsable Principal',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        help='Usuario responsable del análisis de riesgo'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Progreso'),
        ('review', 'En Revisión'),
        ('approved', 'Aprobado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)
    
    # Relaciones con los modelos inferiores
    peligro_ids = fields.One2many(
        'analisis.riesgo.peligro',
        'analisis_id',
        string='Peligros Identificados'
    )
    
    # Campos computados para estadísticas
    total_peligros = fields.Integer(
        string='Total Peligros',
        compute='_compute_estadisticas',
        store=True
    )
    
    total_riesgos = fields.Integer(
        string='Total Riesgos',
        compute='_compute_estadisticas',
        store=True
    )
    
    total_medidas = fields.Integer(
        string='Total Medidas',
        compute='_compute_estadisticas',
        store=True
    )
    
    riesgos_altos = fields.Integer(
        string='Riesgos Altos',
        compute='_compute_estadisticas',
        store=True
    )
    
    riesgos_medios = fields.Integer(
        string='Riesgos Medios',
        compute='_compute_estadisticas',
        store=True
    )
    
    riesgos_bajos = fields.Integer(
        string='Riesgos Bajos',
        compute='_compute_estadisticas',
        store=True
    )
    
    active = fields.Boolean(default=True)
    
    @api.depends('peligro_ids', 'peligro_ids.riesgo_ids', 'peligro_ids.riesgo_ids.medida_ids', 'peligro_ids.riesgo_ids.clasificacion_bruto')
    def _compute_estadisticas(self):
        for record in self:
            peligros = record.peligro_ids
            riesgos = peligros.mapped('riesgo_ids')
            medidas = riesgos.mapped('medida_ids')
            
            record.total_peligros = len(peligros)
            record.total_riesgos = len(riesgos)
            record.total_medidas = len(medidas)
            
            # Clasificar riesgos por nivel (basado en la evaluación bruta)
            altos = riesgos.filtered(lambda r: r.clasificacion_bruto in ['5A', '5B', '4A'])
            medios = riesgos.filtered(lambda r: r.clasificacion_bruto in ['5C', '4B', '3A', '4C', '3B', '2A', '5D'])
            bajos = riesgos.filtered(lambda r: r.clasificacion_bruto and r.clasificacion_bruto not in ['5A', '5B', '4A', '5C', '4B', '3A', '4C', '3B', '2A', '5D'])
            
            record.riesgos_altos = len(altos)
            record.riesgos_medios = len(medios)
            record.riesgos_bajos = len(bajos)
    
    def action_view_peligros(self):
        """Acción para ver los peligros del análisis de riesgo"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Peligros: {self.name}',
            'res_model': 'analisis.riesgo.peligro',
            'view_mode': 'tree,form',
            'domain': [('analisis_id', '=', self.id)],
            'context': {
                'default_analisis_id': self.id,
                'search_default_analisis_id': self.id,
            },
            'target': 'current',
        }
    
    def exportar_excel(self):
        """Exporta todo el análisis de riesgo a un archivo Excel jerárquico con fusión de celdas"""
        self.ensure_one()
        
        # Crear archivo Excel en memoria
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Análisis de Riesgos')
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': '#D7E4BC', 'border': 1
        })
        
        cell_format = workbook.add_format({
            'text_wrap': True, 'valign': 'top', 'border': 1
        })
        
        riesgo_alto_format = workbook.add_format({
            'text_wrap': True, 'valign': 'top', 'border': 1,
            'bg_color': '#FF0000', 'font_color': 'white', 'bold': True
        })
        
        riesgo_medio_format = workbook.add_format({
            'text_wrap': True, 'valign': 'top', 'border': 1,
            'bg_color': '#FFFF00', 'bold': True
        })
        
        riesgo_bajo_format = workbook.add_format({
            'text_wrap': True, 'valign': 'top', 'border': 1,
            'bg_color': '#00FF00'
        })
        
        # Headers
        headers = ['Peligro', 'Riesgo', 'Sev', 'Prob', 'Clas', 'Ctr', 'Sev', 'Prob', 'clas']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Anchos de columna
        column_widths = [20, 50, 8, 8, 10, 60, 8, 8, 10]
        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width)
        
        # Función para obtener formato según clasificación
        def get_format(value):
            if value in ['5A', '5B', '4A']:
                return riesgo_alto_format
            elif value in ['5C', '4B', '3A', '4C', '3B', '2A', '5D']:
                return riesgo_medio_format
            elif value:
                return riesgo_bajo_format
            return cell_format
        
        # Escribir datos y fusionar celdas
        row = 1
        for peligro in self.peligro_ids:
            peligro_start_row = row
            
            for riesgo in peligro.riesgo_ids:
                riesgo_start_row = row
                
                # Si el riesgo no tiene medidas, escribir al menos una línea
                if not riesgo.medida_ids:
                    worksheet.write(row, 0, peligro.nombre, cell_format)
                    worksheet.write(row, 1, riesgo.nombre, cell_format)
                    worksheet.write(row, 2, riesgo.severidad_bruto or '', cell_format)
                    worksheet.write(row, 3, riesgo.probabilidad_bruto or '', cell_format)
                    worksheet.write(row, 4, riesgo.clasificacion_bruto or '', get_format(riesgo.clasificacion_bruto))
                    worksheet.write(row, 5, '', cell_format)  # Sin medida de control
                    worksheet.write(row, 6, riesgo.severidad_neto or '', cell_format)
                    worksheet.write(row, 7, riesgo.probabilidad_neto or '', cell_format)
                    worksheet.write(row, 8, riesgo.clasificacion_neto or '', get_format(riesgo.clasificacion_neto))
                    row += 1
                else:
                    for medida in riesgo.medida_ids:
                        # Escribir datos de la medida
                        worksheet.write(row, 0, peligro.nombre, cell_format)
                        worksheet.write(row, 1, riesgo.nombre, cell_format)
                        worksheet.write(row, 2, riesgo.severidad_bruto or '', cell_format)
                        worksheet.write(row, 3, riesgo.probabilidad_bruto or '', cell_format)
                        worksheet.write(row, 4, riesgo.clasificacion_bruto or '', get_format(riesgo.clasificacion_bruto))
                        worksheet.write(row, 5, medida.nombre, cell_format)
                        worksheet.write(row, 6, riesgo.severidad_neto or '', cell_format)
                        worksheet.write(row, 7, riesgo.probabilidad_neto or '', cell_format)
                        worksheet.write(row, 8, riesgo.clasificacion_neto or '', get_format(riesgo.clasificacion_neto))
                        row += 1
                    
                    # Fusionar celdas del riesgo si tiene múltiples medidas
                    if len(riesgo.medida_ids) > 1:
                        riesgo_end_row = row - 1
                        worksheet.merge_range(riesgo_start_row, 1, riesgo_end_row, 1, riesgo.nombre, cell_format)
                        worksheet.merge_range(riesgo_start_row, 2, riesgo_end_row, 2, riesgo.severidad_bruto or '', cell_format)
                        worksheet.merge_range(riesgo_start_row, 3, riesgo_end_row, 3, riesgo.probabilidad_bruto or '', cell_format)
                        worksheet.merge_range(riesgo_start_row, 4, riesgo_end_row, 4, riesgo.clasificacion_bruto or '', get_format(riesgo.clasificacion_bruto))
                        worksheet.merge_range(riesgo_start_row, 6, riesgo_end_row, 6, riesgo.severidad_neto or '', cell_format)
                        worksheet.merge_range(riesgo_start_row, 7, riesgo_end_row, 7, riesgo.probabilidad_neto or '', cell_format)
                        worksheet.merge_range(riesgo_start_row, 8, riesgo_end_row, 8, riesgo.clasificacion_neto or '', get_format(riesgo.clasificacion_neto))
            
            # Fusionar celda del peligro si tiene múltiples riesgos o múltiples líneas
            total_rows_peligro = row - peligro_start_row
            if total_rows_peligro > 1:
                peligro_end_row = row - 1
                worksheet.merge_range(peligro_start_row, 0, peligro_end_row, 0, peligro.nombre, cell_format)
        
        workbook.close()
        
        # Preparar archivo para descarga
        output.seek(0)
        excel_data = output.getvalue()
        output.close()

        # Crear attachment para descarga
        filename = f"{self.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'res_model': self._name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class AnalisisRiesgoPeligro(models.Model):
    """Modelo para los peligros identificados"""
    _name = 'analisis.riesgo.peligro'
    _description = 'Peligro en Análisis de Riesgo'
    _order = 'sequence, nombre'
    
    analisis_id = fields.Many2one(
        'analisis.riesgo',
        string='Análisis de Riesgo',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(string='Secuencia', default=10)
    
    nombre = fields.Char(
        string='Nombre del Peligro',
        required=True,
        help='Nombre corto identificativo del peligro'
    )
    
    
    # Relación con riesgos
    riesgo_ids = fields.One2many(
        'analisis.riesgo.riesgo',
        'peligro_id',
        string='Riesgos Asociados'
    )
    
    # Campos computados
    total_riesgos = fields.Integer(
        string='Total Riesgos',
        compute='_compute_total_riesgos',
        store=True
    )
    
    active = fields.Boolean(default=True)
    
    @api.depends('riesgo_ids')
    def _compute_total_riesgos(self):
        for record in self:
            record.total_riesgos = len(record.riesgo_ids)
    
    def action_view_riesgos(self):
        """Acción para ver los riesgos de este peligro"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Riesgos: {self.nombre}',
            'res_model': 'analisis.riesgo.riesgo',
            'view_mode': 'tree,form',
            'domain': [('peligro_id', '=', self.id)],
            'context': {
                'default_peligro_id': self.id,
                'search_default_peligro_id': self.id,
            },
            'target': 'current',
        }


class AnalisisRiesgoRiesgo(models.Model):
    """Modelo para los riesgos asociados a peligros"""
    _name = 'analisis.riesgo.riesgo'
    _description = 'Riesgo en Análisis de Riesgo'
    _order = 'sequence, nombre'
    
    peligro_id = fields.Many2one(
        'analisis.riesgo.peligro',
        string='Peligro',
        required=True,
        ondelete='cascade'
    )
    
    analisis_id = fields.Many2one(
        related='peligro_id.analisis_id',
        string='Análisis de Riesgo',
        store=True,
        readonly=True
    )
    
    sequence = fields.Integer(string='Secuencia', default=10)
    
    nombre = fields.Char(
        string='Nombre del Riesgo',
        required=True,
        help='Nombre corto identificativo del riesgo'
    )
    

    # Evaluación bruta (inicial) - se hace a nivel de riesgo
    severidad_bruto = fields.Selection([
        ('A', 'A - Catastrófico'),
        ('B', 'B - Crítico'),
        ('C', 'C - Marginal'),
        ('D', 'D - Despreciable'),
        ('E', 'E - Insignificante')
    ], string='Severidad Bruto', required=True, help='Severidad del riesgo sin controles')

    probabilidad_bruto = fields.Selection([
        ('5', '5 - Muy Probable'),
        ('4', '4 - Probable'),
        ('3', '3 - Ocasional'),
        ('2', '2 - Remoto'),
        ('1', '1 - Improbable')
    ], string='Probabilidad Bruto', required=True, help='Probabilidad del riesgo sin controles')

    clasificacion_bruto = fields.Char(
        string='Clasificación Bruto',
        compute='_compute_clasificacion_bruto',
        store=True,
        help='Clasificación automática del riesgo bruto (ej. 5A)'
    )
    
    # Evaluación neta (después de aplicar todas las medidas)
    severidad_neto = fields.Selection([
        ('A', 'A - Catastrófico'),
        ('B', 'B - Crítico'),
        ('C', 'C - Marginal'),
        ('D', 'D - Despreciable'),
        ('E', 'E - Insignificante')
    ], string='Severidad Neto', help='Severidad del riesgo después de aplicar todas las medidas de control')

    probabilidad_neto = fields.Selection([
        ('5', '5 - Muy Probable'),
        ('4', '4 - Probable'),
        ('3', '3 - Ocasional'),
        ('2', '2 - Remoto'),
        ('1', '1 - Improbable')
    ], string='Probabilidad Neto', help='Probabilidad del riesgo después de aplicar todas las medidas de control')

    clasificacion_neto = fields.Char(
        string='Clasificación Neto',
        compute='_compute_clasificacion_neto',
        store=True,
        help='Clasificación automática del riesgo neto después de todas las medidas'
    )
    
    # Relación con medidas de control
    medida_ids = fields.One2many(
        'analisis.riesgo.medida',
        'riesgo_id',
        string='Medidas de Control'
    )
    
    # Campos computados
    total_medidas = fields.Integer(
        string='Total Medidas',
        compute='_compute_total_medidas',
        store=True
    )
    
    color = fields.Integer(
        string='Color',
        compute='_compute_color',
        help='Color para identificar visualmente el nivel de riesgo'
    )
    
    active = fields.Boolean(default=True)
    
    @api.depends('severidad_bruto', 'probabilidad_bruto')
    def _compute_clasificacion_bruto(self):
        for record in self:
            if record.severidad_bruto and record.probabilidad_bruto:
                record.clasificacion_bruto = f"{record.probabilidad_bruto}{record.severidad_bruto}"
            else:
                record.clasificacion_bruto = False
    
    @api.depends('severidad_neto', 'probabilidad_neto')
    def _compute_clasificacion_neto(self):
        for record in self:
            if record.severidad_neto and record.probabilidad_neto:
                record.clasificacion_neto = f"{record.probabilidad_neto}{record.severidad_neto}"
            else:
                record.clasificacion_neto = False
    
    @api.depends('clasificacion_bruto')
    def _compute_color(self):
        """Asigna color basado en la clasificación de riesgo"""
        color_map = {
            # Rojo para riesgos altos (5A, 5B, 4A)
            '5A': 1, '5B': 1, '4A': 1,
            # Naranja para riesgos medios-altos (5C, 4B, 3A)
            '5C': 7, '4B': 7, '3A': 7,
            # Amarillo para riesgos medios (4C, 3B, 2A, 5D)
            '4C': 3, '3B': 3, '2A': 3, '5D': 3,
            # Verde para riesgos bajos
            '3C': 10, '2B': 10, '1A': 10, '4D': 10, '5E': 10,
            '2C': 10, '1B': 10, '3D': 10, '4E': 10,
            '1C': 10, '2D': 10, '3E': 10,
            '1D': 10, '2E': 10,
            '1E': 10
        }
        
        for record in self:
            record.color = color_map.get(record.clasificacion_bruto, 0)
    
    @api.depends('medida_ids')
    def _compute_total_medidas(self):
        for record in self:
            record.total_medidas = len(record.medida_ids)
    
    def action_view_medidas(self):
        """Acción para ver las medidas de control de este riesgo"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Medidas: {self.nombre}',
            'res_model': 'analisis.riesgo.medida',
            'view_mode': 'tree,form',
            'domain': [('riesgo_id', '=', self.id)],
            'context': {
                'default_riesgo_id': self.id,
                'search_default_riesgo_id': self.id,
            },
            'target': 'current',
        }


class AnalisisRiesgoMedida(models.Model):
    """Modelo para las medidas de control"""
    _name = 'analisis.riesgo.medida'
    _description = 'Medida de Control'
    _order = 'sequence, nombre'
    
    riesgo_id = fields.Many2one(
        'analisis.riesgo.riesgo',
        string='Riesgo',
        required=True,
        ondelete='cascade'
    )
    
    peligro_id = fields.Many2one(
        related='riesgo_id.peligro_id',
        string='Peligro',
        store=True,
        readonly=True
    )
    
    analisis_id = fields.Many2one(
        related='riesgo_id.analisis_id',
        string='Análisis de Riesgo',
        store=True,
        readonly=True
    )
    
    sequence = fields.Integer(string='Secuencia', default=10)
    
    nombre = fields.Char(
        string='Nombre de la Medida',
        required=True,
        help='Nombre corto identificativo de la medida de control'
    )
    


    # Campos de seguimiento y control
    estado = fields.Selection([
        ('draft', 'Borrador'),
        ('planned', 'Planificada'),
        ('in_progress', 'En Implementación'),
        ('implemented', 'Implementada'),
        ('verified', 'Verificada'),
        ('cancelled', 'Cancelada')
    ], string='Estado', default='draft', help='Estado de implementación de la medida')
    
    responsable = fields.Many2one(
        'res.users',
        string='Responsable',
        help='Usuario responsable de implementar esta medida'
    )

    fecha_seguimiento = fields.Date(
        string='Fecha de Seguimiento',
        help='Fecha programada para el próximo seguimiento'
    )
    
    fecha_implementacion = fields.Date(
        string='Fecha de Implementación',
        help='Fecha planificada o real de implementación'
    )

    tarea_asociada = fields.Many2one(
        'project.task',
        string='Tarea Asociada',
        help='Tarea de proyecto creada para gestionar esta medida'
    )
    
    # Campos adicionales
    costo_estimado = fields.Float(
        string='Costo Estimado',
        help='Costo estimado de implementación de la medida'
    )
    
    eficacia = fields.Selection([
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta')
    ], string='Eficacia Esperada', help='Eficacia esperada de la medida de control')
    
    notas = fields.Text(string='Notas Adicionales')
    
    active = fields.Boolean(default=True)

    def crear_tarea(self):
        """Crea una tarea de proyecto asociada a la medida de control"""
        self.ensure_one()
        
        if self.tarea_asociada:
            raise ValidationError("Esta medida ya tiene una tarea asociada.")

        # Buscar un proyecto por defecto o crear uno si no existe
        proyecto = self.env['project.project'].search([('name', '=', 'Gestión de Riesgos')], limit=1)
        if not proyecto:
            proyecto = self.env['project.project'].create({
                'name': 'Gestión de Riesgos',
                'description': 'Proyecto para la gestión de tareas relacionadas con análisis de riesgos'
            })

        # Crear la tarea
        tarea = self.env['project.task'].create({
            'name': f"Medida de Control: {self.nombre[:50]}...",
            'description': f"""
                ANÁLISIS: {self.analisis_id.name}
                PELIGRO: {self.peligro_id.nombre}
                RIESGO: {self.riesgo_id.nombre}
                
                MEDIDA DE CONTROL: {self.nombre}
                
                CLASIFICACIÓN BRUTO: {self.riesgo_id.clasificacion_bruto}
                CLASIFICACIÓN NETO: {self.riesgo_id.clasificacion_neto or 'Pendiente'}
                
                EFICACIA ESPERADA: {dict(self._fields['eficacia'].selection).get(self.eficacia, 'No definida')}
                COSTO ESTIMADO: {self.costo_estimado or 0}
            """,
            'project_id': proyecto.id,
            'user_ids': [(6, 0, [self.responsable.id])] if self.responsable else False,
            'date_deadline': self.fecha_seguimiento or self.fecha_implementacion,
        })

        # Vincular la tarea a la medida
        self.tarea_asociada = tarea.id
        
        # Cambiar estado a planificada
        if self.estado == 'draft':
            self.estado = 'planned'

        return {
            'type': 'ir.actions.act_window',
            'name': 'Tarea Creada',
            'res_model': 'project.task',
            'res_id': tarea.id,
            'view_mode': 'form',
            'target': 'current',
        }