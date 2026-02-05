# -*- coding: utf-8 -*-
"""
Wizard para normalizar etapas en proyectos y tareas con mapeo inteligente.

IMPORTANTE - CONCEPTOS CLAVE:
=============================

1. ETAPAS DE PROYECTO (project.project.type_ids):
   - Son las etapas DISPONIBLES para las tareas de ese proyecto
   - Campo Many2many hacia project.task.type
   - Define qué etapas pueden usarse en el kanban del proyecto
   - Ejemplo: [Pendiente, En proceso, Realizada, Pospuesta, N/A]

2. ETAPAS DE TAREAS (project.task.stage_id):
   - Es la etapa ACTUAL de cada tarea individual
   - Campo Many2one hacia project.task.type
   - Debe estar dentro de las etapas disponibles del proyecto
   - Ejemplo: Tarea X tiene stage_id = "En proceso"

3. LO QUE HACE ESTA HERRAMIENTA:
   a) Normaliza las etapas DISPONIBLES en los proyectos (type_ids)
   b) Actualiza las etapas ACTUALES de las tareas (stage_id) según el mapeo
   c) Mantiene el historial de cambios en el chatter de cada tarea
   
4. FLUJO COMPLETO:
   - Proyecto tiene type_ids = [A, B, C, D]
   - Tarea 1 tiene stage_id = B
   - Tarea 2 tiene stage_id = C
   - Usuario mapea: B→X, C→Y, D→Z
   - Resultado:
     * Proyecto tendrá type_ids = [W, X, Y, Z, N/A] (etapas destino normalizadas)
     * Tarea 1 tendrá stage_id = X (actualizada según mapeo)
     * Tarea 2 tendrá stage_id = Y (actualizada según mapeo)
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class UnificarEtapasSnapshot(models.Model):
    _name = "leulit_tarea.unificar_etapas_snapshot"
    _description = "Snapshot de Estado Anterior para Rollback"
    _order = "create_date desc"

    name = fields.Char(
        string='Descripción',
        required=True,
        default=lambda self: _('Snapshot - %s') % fields.Datetime.now().strftime('%d/%m/%Y %H:%M')
    )
    
    fecha_snapshot = fields.Datetime(
        string='Fecha del Snapshot',
        default=fields.Datetime.now,
        readonly=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    total_proyectos = fields.Integer(
        string='Proyectos Afectados',
        readonly=True
    )
    
    total_tareas = fields.Integer(
        string='Tareas Afectadas',
        readonly=True
    )
    
    estado_proyectos = fields.Text(
        string='Estado de Proyectos (JSON)',
        help='Información de etapas por proyecto antes del cambio',
        readonly=True
    )
    
    estado_tareas = fields.Text(
        string='Estado de Tareas (JSON)',
        help='Información de etapas por tarea antes del cambio',
        readonly=True
    )
    
    activo = fields.Boolean(
        string='Activo',
        default=True,
        help='Indica si este snapshot puede usarse para rollback'
    )
    
    def action_rollback(self):
        """
        Restaura el estado anterior desde este snapshot.
        """
        self.ensure_one()
        
        if not self.activo:
            raise UserError(_('Este snapshot ya no está activo y no puede usarse para rollback'))
        
        import json
        
        # Restaurar proyectos
        estado_proyectos = json.loads(self.estado_proyectos)
        proyectos_restaurados = 0
        
        for proyecto_data in estado_proyectos:
            proyecto = self.env['project.project'].browse(proyecto_data['id'])
            if proyecto.exists():
                try:
                    proyecto.write({
                        'type_ids': [(6, 0, proyecto_data['type_ids'])]
                    })
                    proyectos_restaurados += 1
                except Exception:
                    _logger.exception('Error restaurando proyecto %s (ID: %s) desde snapshot %s',
                                      proyecto.name, proyecto.id, self.name)
                    # continuar con los demás proyectos
        
        # Restaurar tareas
        estado_tareas = json.loads(self.estado_tareas)
        tareas_restauradas = 0
        
        for tarea_data in estado_tareas:
            tarea = self.env['project.task'].browse(tarea_data['id'])
            if tarea.exists():
                try:
                    tarea.write({
                        'stage_id': tarea_data['stage_id']
                    })
                    tareas_restauradas += 1
                except Exception:
                    _logger.exception('Error restaurando tarea %s (ID: %s) desde snapshot %s',
                                      tarea.name, tarea.id, self.name)
                    # continuar con las demás tareas
        
        # Desactivar este snapshot
        self.write({'activo': False})
        
        _logger.info('Rollback completado desde snapshot %s: %s proyectos, %s tareas restauradas',
                     self.name, proyectos_restaurados, tareas_restauradas)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✓ Rollback Completado'),
                'message': _('Estado restaurado exitosamente:\n\n'
                           '• Proyectos: %s\n'
                           '• Tareas: %s\n\n'
                           'El snapshot ha sido desactivado.') % (proyectos_restaurados, tareas_restauradas),
                'type': 'success',
                'sticky': True,
            }
        }


class UnificarEtapasMapeoLinea(models.TransientModel):
    _name = "leulit_tarea.unificar_etapas_mapeo_linea"
    _description = "Línea de Mapeo de Etapas"
    _order = "etapa_origen_id"

    wizard_id = fields.Many2one(
        'leulit_tarea.unificar_etapas_wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    etapa_origen_id = fields.Many2one(
        'project.task.type',
        string='Etapa Existente',
        required=True,
        help='Etapa actual en uso en los proyectos'
    )
    
    etapa_destino_id = fields.Many2one(
        'project.task.type',
        string='Etapa Destino',
        required=True,
        help='Etapa normalizada a la que se mapeará'
    )
    
    etapa_origen_nombre = fields.Char(
        related='etapa_origen_id.name',
        string='Nombre Origen',
        readonly=True
    )
    
    etapa_destino_nombre = fields.Char(
        related='etapa_destino_id.name',
        string='Nombre Destino',
        readonly=True
    )
    
    proyectos_afectados = fields.Integer(
        string='Proyectos Afectados',
        help='Número de proyectos que usan esta etapa'
    )
    
    tareas_afectadas = fields.Integer(
        string='Tareas Afectadas',
        help='Número de tareas que usan esta etapa'
    )


class UnificarEtapasWizard(models.TransientModel):
    _name = "leulit_tarea.unificar_etapas_wizard"
    _description = "Wizard para Normalizar Etapas de Proyectos y Tareas"

    # Etapas destino predefinidas (se crean si no existen)
    ETAPAS_DESTINO_PROYECTO = [
        'Borrador',
        'En proceso', 
        'Finalizado'
    ]
    
    ETAPAS_DESTINO_TAREA = [
        'Pendiente',
        'En proceso',
        'Realizada',
        'Pospuesta',
        'N/A'
    ]
    
    aplicar_a_proyectos = fields.Boolean(
        string='Aplicar a Todos los Proyectos',
        default=True,
        help='Si está marcado, se procesarán todos los proyectos del sistema'
    )
    
    proyecto_ids = fields.Many2many(
        'project.project',
        string='Proyectos Específicos',
        help='Si no se marca "Aplicar a Todos los Proyectos", selecciona los proyectos específicos'
    )
    
    estado = fields.Selection([
        ('paso1', 'Paso 1: Selección'),
        ('paso2', 'Paso 2: Mapeo de Etapas'),
        ('paso3', 'Paso 3: Simulación de Cambios'),
    ], string='Estado', default='paso1')
    
    modo_ejecucion = fields.Selection([
        ('simulacion', 'Simulación (No aplica cambios)'),
        ('real', 'Ejecución Real (Aplica cambios)'),
    ], string='Modo de Ejecución', default='simulacion')
    
    crear_snapshot = fields.Boolean(
        string='Crear Snapshot para Rollback',
        default=True,
        help='Guarda el estado actual antes de aplicar cambios para poder revertir'
    )
    
    limpiar_etapas_obsoletas = fields.Boolean(
        string='Eliminar Etapas Obsoletas',
        default=False,
        help='Después de normalizar, elimina las etapas antiguas que ya no estén en uso. '
             'SOLO se eliminan etapas que no estén asignadas a ningún proyecto ni tarea.'
    )
    
    snapshot_id = fields.Many2one(
        'leulit_tarea.unificar_etapas_snapshot',
        string='Snapshot Creado',
        readonly=True
    )
    
    etapas_eliminadas = fields.Integer(
        string='Etapas Obsoletas Eliminadas',
        readonly=True
    )
    
    mapeo_linea_ids = fields.One2many(
        'leulit_tarea.unificar_etapas_mapeo_linea',
        'wizard_id',
        string='Mapeo de Etapas'
    )
    
    total_proyectos = fields.Integer(
        string='Total Proyectos',
        readonly=True
    )
    
    total_etapas_origen = fields.Integer(
        string='Total Etapas Existentes',
        readonly=True
    )
    
    # Campos de simulación
    simulacion_resultado = fields.Text(
        string='Resultado de Simulación',
        readonly=True
    )
    
    simulacion_stats = fields.Text(
        string='Estadísticas de Simulación',
        readonly=True
    )

    @api.constrains('aplicar_a_proyectos', 'proyecto_ids')
    def _check_proyectos(self):
        """
        Validación: En paso 1, debe haber al menos un proyecto seleccionado o marcar aplicar a todos.
        """
        for wizard in self:
            if wizard.estado == 'paso1':
                if not wizard.aplicar_a_proyectos and not wizard.proyecto_ids:
                    raise UserError(_('Debes seleccionar al menos un proyecto o marcar "Aplicar a Todos los Proyectos"'))

    def _crear_etapas_destino(self):
        """
        Crea las etapas destino si no existen y retorna sus IDs.
        """
        TaskType = self.env['project.task.type']
        etapas_creadas = []
        
        # Crear etapas para tareas
        for nombre_etapa in self.ETAPAS_DESTINO_TAREA:
            etapa = TaskType.search([('name', '=', nombre_etapa)], limit=1)
            if not etapa:
                etapa = TaskType.create({
                    'name': nombre_etapa,
                    'description': f'Etapa normalizada: {nombre_etapa}',
                })
                _logger.info('Etapa destino creada: %s (ID: %s)', nombre_etapa, etapa.id)
                etapas_creadas.append(nombre_etapa)
            
        if etapas_creadas:
            _logger.info('Total etapas destino creadas: %s - %s', len(etapas_creadas), ', '.join(etapas_creadas))
        
        return True

    def _obtener_etapas_existentes(self, proyectos):
        """
        Obtiene todas las etapas únicas usadas en los proyectos seleccionados.
        Retorna diccionario con estadísticas por etapa.
        """
        etapas_info = {}
        
        # Obtener etapas de proyectos
        for proyecto in proyectos:
            for etapa in proyecto.type_ids:
                if etapa.id not in etapas_info:
                    etapas_info[etapa.id] = {
                        'etapa': etapa,
                        'proyectos': 0,
                        'tareas': 0
                    }
                etapas_info[etapa.id]['proyectos'] += 1
        
        # Contar tareas por etapa
        tareas = self.env['project.task'].search([('project_id', 'in', proyectos.ids)])
        for tarea in tareas:
            if tarea.stage_id and tarea.stage_id.id in etapas_info:
                etapas_info[tarea.stage_id.id]['tareas'] += 1
        
        return etapas_info

    def action_analizar_etapas(self):
        """
        Paso 1: Analiza los proyectos y genera el mapeo de etapas.
        """
        self.ensure_one()
        
        # Determinar proyectos a procesar
        if self.aplicar_a_proyectos:
            proyectos = self.env['project.project'].search([])
        else:
            proyectos = self.proyecto_ids
        
        if not proyectos:
            raise UserError(_('No se encontraron proyectos para procesar'))
        
        _logger.info('Analizando etapas para %s proyectos', len(proyectos))
        
        # Crear etapas destino si no existen
        self._crear_etapas_destino()
        
        # Obtener todas las etapas existentes
        etapas_info = self._obtener_etapas_existentes(proyectos)
        
        # Obtener etapas destino disponibles
        etapas_destino = self.env['project.task.type'].search([
            ('name', 'in', self.ETAPAS_DESTINO_TAREA)
        ])
        
        if not etapas_destino:
            raise UserError(_('No se encontraron etapas destino. Verifica la configuración.'))
        
        # Crear líneas de mapeo
        mapeo_lineas = []
        for etapa_id, info in etapas_info.items():
            etapa_origen = info['etapa']
            
            # Buscar coincidencia exacta con etapa destino
            etapa_destino = etapas_destino.filtered(lambda e: e.name == etapa_origen.name)
            if not etapa_destino:
                # Si no hay coincidencia, usar la primera etapa destino por defecto
                etapa_destino = etapas_destino[0]
            
            mapeo_lineas.append((0, 0, {
                'etapa_origen_id': etapa_origen.id,
                'etapa_destino_id': etapa_destino.id,
                'proyectos_afectados': info['proyectos'],
                'tareas_afectadas': info['tareas'],
            }))
        
        # Actualizar wizard
        self.write({
            'estado': 'paso2',
            'mapeo_linea_ids': [(5, 0, 0)] + mapeo_lineas,  # Eliminar anteriores y crear nuevas
            'total_proyectos': len(proyectos),
            'total_etapas_origen': len(etapas_info),
        })
        
        _logger.info('Análisis completado: %s etapas únicas encontradas', len(etapas_info))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_simular_cambios(self):
        """
        Paso 2.5: Simula los cambios sin aplicarlos y muestra el resultado.
        """
        self.ensure_one()
        
        if not self.mapeo_linea_ids:
            raise UserError(_('No hay mapeos de etapas definidos'))
        
        # Determinar proyectos a procesar
        if self.aplicar_a_proyectos:
            proyectos = self.env['project.project'].search([])
        else:
            proyectos = self.proyecto_ids
        
        # Simular cambios (sin aplicarlos)
        stats = self._simular_normalizacion(proyectos)
        
        # Generar reporte detallado
        resultado_texto = self._generar_reporte_simulacion(stats, proyectos)
        stats_texto = self._generar_stats_simulacion(stats)
        
        # Actualizar wizard
        self.write({
            'estado': 'paso3',
            'simulacion_resultado': resultado_texto,
            'simulacion_stats': stats_texto,
        })
        
        _logger.info('Simulación completada: %s', stats)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _simular_normalizacion(self, proyectos):
        """
        Simula la normalización sin aplicar cambios.
        Retorna estadísticas detalladas.
        """
        stats = {
            'proyectos_sin_etapas': [],
            'proyectos_sin_cambios': [],
            'proyectos_con_cambios': [],
            'etapas_a_sustituir': [],
            'etapas_a_añadir': [],
            'tareas_a_actualizar': [],
        }
        
        # Crear diccionario de mapeo
        mapeo_dict = {linea.etapa_origen_id.id: linea.etapa_destino_id for linea in self.mapeo_linea_ids}
        
        # Obtener etapas destino únicas
        etapas_destino_ids = set([linea.etapa_destino_id.id for linea in self.mapeo_linea_ids])
        
        # Analizar cada proyecto
        for proyecto in proyectos:
            etapas_actuales = proyecto.type_ids
            
            if not etapas_actuales:
                # Proyecto sin etapas
                stats['proyectos_sin_etapas'].append({
                    'proyecto': proyecto.name,
                    'id': proyecto.id,
                    'etapas_a_añadir': len(etapas_destino_ids)
                })
            else:
                cambios = []
                etapas_faltantes = set()
                
                for etapa in etapas_actuales:
                    if etapa.id in etapas_destino_ids:
                        # Etapa ya correcta
                        pass
                    elif etapa.id in mapeo_dict:
                        # Etapa a sustituir
                        etapa_destino = mapeo_dict[etapa.id]
                        cambios.append({
                            'tipo': 'sustituir',
                            'origen': etapa.name,
                            'destino': etapa_destino.name
                        })
                        stats['etapas_a_sustituir'].append({
                            'proyecto': proyecto.name,
                            'etapa_origen': etapa.name,
                            'etapa_destino': etapa_destino.name
                        })
                
                # Detectar etapas faltantes
                etapas_proyecto_ids = set([e.id for e in etapas_actuales])
                etapas_faltantes = etapas_destino_ids - etapas_proyecto_ids
                
                if etapas_faltantes:
                    etapas_faltantes_obj = self.env['project.task.type'].browse(list(etapas_faltantes))
                    for etapa in etapas_faltantes_obj:
                        cambios.append({
                            'tipo': 'añadir',
                            'etapa': etapa.name
                        })
                        stats['etapas_a_añadir'].append({
                            'proyecto': proyecto.name,
                            'etapa': etapa.name
                        })
                
                if cambios:
                    stats['proyectos_con_cambios'].append({
                        'proyecto': proyecto.name,
                        'id': proyecto.id,
                        'cambios': cambios
                    })
                else:
                    stats['proyectos_sin_cambios'].append({
                        'proyecto': proyecto.name,
                        'id': proyecto.id
                    })
        
        # Analizar tareas
        tareas = self.env['project.task'].search([('project_id', 'in', proyectos.ids)])
        for tarea in tareas:
            if tarea.stage_id and tarea.stage_id.id in mapeo_dict:
                etapa_destino = mapeo_dict[tarea.stage_id.id]
                if tarea.stage_id.id != etapa_destino.id:
                    stats['tareas_a_actualizar'].append({
                        'tarea': tarea.name,
                        'id': tarea.id,
                        'proyecto': tarea.project_id.name,
                        'etapa_actual': tarea.stage_id.name,
                        'etapa_nueva': etapa_destino.name
                    })
        
        return stats

    def _generar_reporte_simulacion(self, stats, proyectos):
        """
        Genera un reporte de texto detallado de los cambios simulados.
        """
        lineas = []
        
        lineas.append('═' * 60)
        lineas.append('REPORTE DE SIMULACIÓN - CAMBIOS A REALIZAR')
        lineas.append('═' * 60)
        lineas.append('')
        
        # Proyectos sin etapas
        if stats['proyectos_sin_etapas']:
            lineas.append(f"📝 PROYECTOS SIN ETAPAS ({len(stats['proyectos_sin_etapas'])})")
            lineas.append('─' * 60)
            for p in stats['proyectos_sin_etapas'][:10]:  # Mostrar máximo 10
                lineas.append(f"  • {p['proyecto']} → Se añadirán {p['etapas_a_añadir']} etapas")
            if len(stats['proyectos_sin_etapas']) > 10:
                lineas.append(f"  ... y {len(stats['proyectos_sin_etapas']) - 10} más")
            lineas.append('')
        
        # Proyectos con cambios
        if stats['proyectos_con_cambios']:
            lineas.append(f"🔄 PROYECTOS CON CAMBIOS ({len(stats['proyectos_con_cambios'])})")
            lineas.append('─' * 60)
            for p in stats['proyectos_con_cambios'][:10]:
                lineas.append(f"  • {p['proyecto']}:")
                for cambio in p['cambios'][:5]:
                    if cambio['tipo'] == 'sustituir':
                        lineas.append(f"    - Sustituir '{cambio['origen']}' → '{cambio['destino']}'")
                    elif cambio['tipo'] == 'añadir':
                        lineas.append(f"    - Añadir etapa '{cambio['etapa']}'")
            if len(stats['proyectos_con_cambios']) > 10:
                lineas.append(f"  ... y {len(stats['proyectos_con_cambios']) - 10} más")
            lineas.append('')
        
        # Proyectos sin cambios
        if stats['proyectos_sin_cambios']:
            lineas.append(f"✓ PROYECTOS SIN CAMBIOS ({len(stats['proyectos_sin_cambios'])})")
            lineas.append('─' * 60)
            for p in stats['proyectos_sin_cambios'][:5]:
                lineas.append(f"  • {p['proyecto']} (ya está correcto)")
            if len(stats['proyectos_sin_cambios']) > 5:
                lineas.append(f"  ... y {len(stats['proyectos_sin_cambios']) - 5} más")
            lineas.append('')
        
        # Tareas
        if stats['tareas_a_actualizar']:
            lineas.append(f"📋 TAREAS A ACTUALIZAR ({len(stats['tareas_a_actualizar'])})")
            lineas.append('─' * 60)
            for t in stats['tareas_a_actualizar'][:10]:
                lineas.append(f"  • [{t['proyecto']}] {t['tarea']}")
                lineas.append(f"    '{t['etapa_actual']}' → '{t['etapa_nueva']}'")
            if len(stats['tareas_a_actualizar']) > 10:
                lineas.append(f"  ... y {len(stats['tareas_a_actualizar']) - 10} más")
            lineas.append('')
        
        lineas.append('═' * 60)
        
        return '\n'.join(lineas)

    def _generar_stats_simulacion(self, stats):
        """
        Genera estadísticas resumidas de la simulación.
        """
        return (
            f"Proyectos sin etapas: {len(stats['proyectos_sin_etapas'])}\n"
            f"Proyectos con cambios: {len(stats['proyectos_con_cambios'])}\n"
            f"Proyectos sin cambios: {len(stats['proyectos_sin_cambios'])}\n"
            f"Etapas a sustituir: {len(stats['etapas_a_sustituir'])}\n"
            f"Etapas a añadir: {len(stats['etapas_a_añadir'])}\n"
            f"Tareas a actualizar: {len(stats['tareas_a_actualizar'])}"
        )

    def action_volver_paso1(self):
        """
        Vuelve al paso 1 de selección.
        """
        self.ensure_one()
        self.write({
            'estado': 'paso1',
            'mapeo_linea_ids': [(5, 0, 0)],  # Limpiar mapeos
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_unificar_etapas(self):
        """
        Paso 3: Ejecuta la normalización de etapas según el mapeo definido.
        """
        self.ensure_one()
        
        if self.modo_ejecucion == 'simulacion':
            raise UserError(_('Estás en modo SIMULACIÓN. Cambia a "Ejecución Real" para aplicar los cambios.'))
        
        if not self.mapeo_linea_ids:
            raise UserError(_('No hay mapeos de etapas definidos. Vuelve al paso 1 y analiza los proyectos.'))
        
        # Determinar proyectos a procesar
        if self.aplicar_a_proyectos:
            proyectos = self.env['project.project'].search([])
        else:
            proyectos = self.proyecto_ids
        
        # Crear snapshot antes de aplicar cambios
        snapshot_id = None
        if self.crear_snapshot:
            snapshot_id = self._crear_snapshot(proyectos)
            self.write({'snapshot_id': snapshot_id.id})
            _logger.info('Snapshot creado: %s (ID: %s)', snapshot_id.name, snapshot_id.id)
        
        # Estadísticas
        stats = {
            'proyectos_actualizados': 0,
            'etapas_sustituidas': 0,
            'etapas_añadidas': 0,
            'tareas_actualizadas': 0,
            'proyectos_sin_cambios': 0,
        }
        
        _logger.info('Iniciando normalización de etapas para %s proyectos', len(proyectos))
        
        # Crear diccionario de mapeo para acceso rápido
        mapeo_dict = {linea.etapa_origen_id.id: linea.etapa_destino_id for linea in self.mapeo_linea_ids}
        
        # Obtener todas las etapas destino únicas
        etapas_destino = self.env['project.task.type'].browse([
            linea.etapa_destino_id.id for linea in self.mapeo_linea_ids
        ])
        etapas_destino_ids = set(etapas_destino.ids)
        
        # Procesar cada proyecto
        for proyecto in proyectos:
            cambios_proyecto = self._normalizar_proyecto(proyecto, mapeo_dict, etapas_destino_ids, stats)
            
            if cambios_proyecto:
                stats['proyectos_actualizados'] += 1
            else:
                stats['proyectos_sin_cambios'] += 1
        
        # Procesar tareas
        self._normalizar_tareas(proyectos, mapeo_dict, stats)
        
        # Limpiar etapas obsoletas si está marcada la opción
        if self.limpiar_etapas_obsoletas:
            etapas_eliminadas = self._limpiar_etapas_obsoletas(etapas_destino, proyectos)
            stats['etapas_eliminadas'] = etapas_eliminadas
            self.write({'etapas_eliminadas': etapas_eliminadas})
        
        _logger.info('Normalización completada: %s', stats)
        
        # Mostrar mensaje de éxito con link a snapshot
        mensaje = self._generar_mensaje_resultado(stats)
        if snapshot_id:
            mensaje += _('\n\n💾 Snapshot creado: %s\n'
                        'Puedes revertir los cambios desde: Gestión tareas → Configuración → Snapshots de Rollback') % snapshot_id.name
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✓ Normalización de Etapas Completada'),
                'message': mensaje,
                'type': 'success',
                'sticky': True,
            }
        }

    def _crear_snapshot(self, proyectos):
        """
        Crea un snapshot del estado actual antes de aplicar cambios.
        """
        import json
        
        # Guardar estado de proyectos
        estado_proyectos = []
        for proyecto in proyectos:
            estado_proyectos.append({
                'id': proyecto.id,
                'name': proyecto.name,
                'type_ids': proyecto.type_ids.ids
            })
        
        # Guardar estado de tareas
        tareas = self.env['project.task'].search([('project_id', 'in', proyectos.ids)])
        estado_tareas = []
        for tarea in tareas:
            estado_tareas.append({
                'id': tarea.id,
                'name': tarea.name,
                'stage_id': tarea.stage_id.id if tarea.stage_id else False
            })
        
        # Crear snapshot
        try:
            snapshot = self.env['leulit_tarea.unificar_etapas_snapshot'].create({
                'name': _('Snapshot antes de normalización - %s proyectos') % len(proyectos),
                'total_proyectos': len(proyectos),
                'total_tareas': len(tareas),
                'estado_proyectos': json.dumps(estado_proyectos, ensure_ascii=False, indent=2),
                'estado_tareas': json.dumps(estado_tareas, ensure_ascii=False, indent=2),
            })
        except Exception:
            _logger.exception('Error creando snapshot antes de normalización para %s proyectos', len(proyectos))
            raise
        
        return snapshot

    def _normalizar_proyecto(self, proyecto, mapeo_dict, etapas_destino_ids, stats):
        """
        Normaliza las etapas DISPONIBLES de un proyecto (type_ids) según el mapeo.
        
        IMPORTANTE: Este método modifica las etapas disponibles del proyecto,
        NO las etapas de las tareas. Las tareas se actualizan en _normalizar_tareas().
        
        Args:
            proyecto: Registro de project.project
            mapeo_dict: Diccionario {etapa_origen_id: etapa_destino_obj}
            etapas_destino_ids: Set de IDs de etapas destino normalizadas
            stats: Diccionario de estadísticas a actualizar
            
        Returns:
            bool: True si hubo cambios en el proyecto
        """
        hubo_cambios = False
        etapas_actuales = proyecto.type_ids  # Many2many: etapas DISPONIBLES
        nuevas_etapas_ids = set()
        
        if not etapas_actuales:
            # Caso 1: Proyecto sin etapas → asignar todas las etapas destino
            nuevas_etapas_ids = etapas_destino_ids
            stats['etapas_añadidas'] += len(etapas_destino_ids)
            hubo_cambios = True
            _logger.info('Proyecto "%s" sin etapas - Asignadas %s etapas destino', 
                        proyecto.name, len(etapas_destino_ids))
        else:
            # Caso 2: Proyecto con etapas
            for etapa in etapas_actuales:
                if etapa.id in etapas_destino_ids:
                    # Caso 2a: Etapa coincide con etapa destino → mantener
                    nuevas_etapas_ids.add(etapa.id)
                elif etapa.id in mapeo_dict:
                    # Caso 2b: Etapa mapeada → sustituir
                    etapa_destino = mapeo_dict[etapa.id]
                    nuevas_etapas_ids.add(etapa_destino.id)
                    stats['etapas_sustituidas'] += 1
                    hubo_cambios = True
                    _logger.debug('Etapa "%s" sustituida por "%s" en proyecto "%s"', 
                                 etapa.name, etapa_destino.name, proyecto.name)
            
            # Caso 2c: Añadir etapas destino que no están en el proyecto
            etapas_faltantes = etapas_destino_ids - nuevas_etapas_ids
            if etapas_faltantes:
                nuevas_etapas_ids.update(etapas_faltantes)
                stats['etapas_añadidas'] += len(etapas_faltantes)
                hubo_cambios = True
                _logger.debug('Añadidas %s etapas faltantes al proyecto "%s"', 
                             len(etapas_faltantes), proyecto.name)
        
        # Actualizar proyecto si hay cambios
        if hubo_cambios:
            try:
                proyecto.write({
                    'type_ids': [(6, 0, list(nuevas_etapas_ids))]
                })
            except Exception:
                _logger.exception('Error actualizando proyecto "%s" (ID: %s)', proyecto.name, proyecto.id)
                raise
            _logger.info('Proyecto actualizado: "%s" (ID: %s) - Total etapas disponibles: %s', 
                        proyecto.name, proyecto.id, len(nuevas_etapas_ids))
        
        return hubo_cambios

    def _normalizar_tareas(self, proyectos, mapeo_dict, stats):
        """
        Normaliza las etapas ACTUALES de las tareas (stage_id) según el mapeo.
        
        IMPORTANTE: Este método actualiza la etapa actual de cada tarea individual,
        NO las etapas disponibles del proyecto. Los proyectos se actualizan en _normalizar_proyecto().
        
        Este cambio se registra en el chatter/historial de cada tarea automáticamente
        por el mecanismo de tracking de Odoo en el campo stage_id.
        
        Args:
            proyectos: Recordset de proyectos afectados
            mapeo_dict: Diccionario {etapa_origen_id: etapa_destino_obj}
            stats: Diccionario de estadísticas a actualizar
        """
        tareas = self.env['project.task'].search([('project_id', 'in', proyectos.ids)])
        
        _logger.info('Procesando %s tareas de %s proyectos', len(tareas), len(proyectos))
        
        for tarea in tareas:
            if tarea.stage_id and tarea.stage_id.id in mapeo_dict:
                etapa_destino = mapeo_dict[tarea.stage_id.id]
                
                # Solo actualizar si la etapa destino es diferente
                if tarea.stage_id.id != etapa_destino.id:
                    etapa_origen_nombre = tarea.stage_id.name
                    try:
                        tarea.write({
                            'stage_id': etapa_destino.id
                        })
                    except Exception:
                        _logger.exception('Error actualizando tarea "%s" (ID: %s)', tarea.name, tarea.id)
                        raise
                    stats['tareas_actualizadas'] += 1
                    _logger.debug('Tarea "%s" (ID: %s) actualizada: "%s" → "%s"', 
                                 tarea.name, tarea.id, etapa_origen_nombre, etapa_destino.name)
        
        _logger.info('Total tareas actualizadas: %s de %s', stats['tareas_actualizadas'], len(tareas))

    def _generar_mensaje_resultado(self, stats):
        """
        Genera el mensaje de resultado con las estadísticas.
        """
        mensaje_base = _(
            'Normalización completada exitosamente:\n\n'
            '📊 Estadísticas:\n'
            '• Proyectos actualizados: {proyectos_actualizados}\n'
            '• Proyectos sin cambios: {proyectos_sin_cambios}\n'
            '• Etapas sustituidas: {etapas_sustituidas}\n'
            '• Etapas añadidas: {etapas_añadidas}\n'
            '• Tareas actualizadas: {tareas_actualizadas}\n'
        ).format(**stats)
        
        if stats.get('etapas_eliminadas', 0) > 0:
            mensaje_base += _('• Etapas obsoletas eliminadas: {etapas_eliminadas}\n').format(**stats)
        
        mensaje_base += _('\n✓ El historial de cambios se ha mantenido en todas las tareas.')
        
        return mensaje_base
    
    def _limpiar_etapas_obsoletas(self, etapas_destino, proyectos_procesados):
        """
        Elimina etapas obsoletas que ya no están en uso después de la normalización.
        
        SEGURIDAD: Solo elimina etapas que cumplan TODAS estas condiciones:
        1. NO son etapas destino (normalizadas)
        2. NO están asignadas a ningún proyecto como etapa disponible
        3. NO están siendo usadas por ninguna tarea como etapa actual
        
        Args:
            etapas_destino: Recordset de etapas destino normalizadas
            proyectos_procesados: Recordset de proyectos que fueron normalizados
            
        Returns:
            int: Cantidad de etapas eliminadas
        """
        TaskType = self.env['project.task.type']
        
        # Obtener todas las etapas del sistema
        todas_las_etapas = TaskType.search([])
        
        # Etapas obsoletas candidatas = todas - etapas destino
        etapas_candidatas = todas_las_etapas - etapas_destino
        
        if not etapas_candidatas:
            _logger.info('No hay etapas obsoletas candidatas para eliminar')
            return 0
        
        _logger.info('Analizando %s etapas candidatas para eliminación', len(etapas_candidatas))
        
        etapas_eliminadas = 0
        etapas_retenidas = []
        
        for etapa in etapas_candidatas:
            # Verificar si algún proyecto la tiene como etapa disponible
            proyectos_con_etapa = self.env['project.project'].search_count([
                ('type_ids', 'in', etapa.id)
            ])
            
            if proyectos_con_etapa > 0:
                etapas_retenidas.append(f'{etapa.name} (en {proyectos_con_etapa} proyectos)')
                _logger.debug('Etapa "%s" RETENIDA: usada en %s proyectos', 
                             etapa.name, proyectos_con_etapa)
                continue
            
            # Verificar si alguna tarea la usa como etapa actual
            tareas_con_etapa = self.env['project.task'].search_count([
                ('stage_id', '=', etapa.id)
            ])
            
            if tareas_con_etapa > 0:
                etapas_retenidas.append(f'{etapa.name} (en {tareas_con_etapa} tareas)')
                _logger.debug('Etapa "%s" RETENIDA: usada en %s tareas', 
                             etapa.name, tareas_con_etapa)
                continue
            
            # Seguro eliminar: no está en uso en ningún lado
            try:
                etapa_nombre = etapa.name
                etapa.unlink()
                etapas_eliminadas += 1
                _logger.info('✓ Etapa obsoleta eliminada: "%s" (ID: %s)', etapa_nombre, etapa.id)
            except Exception as e:
                _logger.exception('✗ Error al eliminar etapa "%s": %s', etapa.name, str(e))
        
        # Log de resumen
        if etapas_eliminadas > 0:
            _logger.info('Limpieza completada: %s etapas obsoletas eliminadas', etapas_eliminadas)
        
        if etapas_retenidas:
            _logger.info('Etapas retenidas (aún en uso): %s', ', '.join(etapas_retenidas[:5]))
            if len(etapas_retenidas) > 5:
                _logger.info('... y %s más', len(etapas_retenidas) - 5)
        
        return etapas_eliminadas
