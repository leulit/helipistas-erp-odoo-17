# -*- coding: utf-8 -*-
import logging
from datetime import date
from odoo import api, models, _

_logger = logging.getLogger(__name__)


class AiToolRegistry(models.AbstractModel):
    """
    Registro central de herramientas disponibles para el agente IA.

    Cada herramienta es un método de este modelo. El controlador llama a
    get_tool_definitions() para obtener el schema JSON que se envía al LLM, y
    a execute_tool() para ejecutar la herramienta elegida por el LLM.

    IMPORTANTE: execute_tool recibe el `env` del usuario autenticado (request.env)
    para que las ACLs y record rules de Odoo se apliquen automáticamente.
    """
    _name = 'ai.tool.registry'
    _description = 'Registro de herramientas IA'

    # ------------------------------------------------------------------
    # Definiciones de herramientas (schema JSON Schema compatible con
    # Claude API y Ollama tool-calling)
    # ------------------------------------------------------------------

    TOOLS = [
        {
            'name': 'get_course_status',
            'description': (
                'Obtiene el estado de finalización de cursos/encuestas de Odoo Survey. '
                'Devuelve una lista de participantes con su estado (completado, en progreso, sin iniciar).'
            ),
            'input_schema': {
                'type': 'object',
                'properties': {
                    'survey_title': {
                        'type': 'string',
                        'description': 'Título o nombre parcial del curso/encuesta a consultar. Opcional.',
                    },
                    'only_pending': {
                        'type': 'boolean',
                        'description': 'Si es true, devuelve solo los que NO han completado el curso.',
                    },
                },
                'required': [],
            },
        },
        {
            'name': 'get_project_delays',
            'description': (
                'Detecta tareas de proyecto con retraso (fecha límite superada y no finalizadas). '
                'Devuelve la lista de tareas con nombre, proyecto, responsable y días de retraso.'
            ),
            'input_schema': {
                'type': 'object',
                'properties': {
                    'project_name': {
                        'type': 'string',
                        'description': 'Nombre o parte del nombre del proyecto a filtrar. Opcional.',
                    },
                    'days_overdue': {
                        'type': 'integer',
                        'description': 'Mínimo de días de retraso para incluir la tarea. Por defecto 0.',
                    },
                },
                'required': [],
            },
        },
        {
            'name': 'validate_compliance',
            'description': (
                'Verifica si un empleado cumple con los requisitos de RRHH: '
                'documentación completa, cursos obligatorios finalizados, etc.'
            ),
            'input_schema': {
                'type': 'object',
                'properties': {
                    'employee_name': {
                        'type': 'string',
                        'description': 'Nombre o parte del nombre del empleado a verificar.',
                    },
                },
                'required': ['employee_name'],
            },
        },
    ]

    @api.model
    def get_tool_definitions(self):
        """Retorna la lista de herramientas en formato compatible con Claude y Ollama."""
        return self.TOOLS

    @api.model
    def execute_tool(self, name, arguments, env):
        """
        Ejecuta la herramienta indicada usando el `env` del usuario autenticado.

        :param name: nombre de la herramienta (str)
        :param arguments: dict con los argumentos enviados por el LLM
        :param env: odoo.api.Environment del usuario autenticado
        :return: dict con los resultados o un mensaje de error
        """
        handlers = {
            'get_course_status': self._tool_get_course_status,
            'get_project_delays': self._tool_get_project_delays,
            'validate_compliance': self._tool_validate_compliance,
        }
        handler = handlers.get(name)
        if not handler:
            return {'error': _('Herramienta desconocida: %s') % name}
        try:
            return handler(arguments, env)
        except Exception as e:
            _logger.exception('Error ejecutando herramienta IA "%s"', name)
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # Handlers de herramientas
    # ------------------------------------------------------------------

    def _tool_get_course_status(self, args, env):
        """Consulta survey.user_input para obtener el estado de cursos."""
        survey_title = args.get('survey_title', '')
        only_pending = args.get('only_pending', False)

        domain = []
        if survey_title:
            domain.append(('survey_id.title', 'ilike', survey_title))
        if only_pending:
            domain.append(('state', '!=', 'done'))

        inputs = env['survey.user_input'].search(domain, limit=50)
        result = []
        for inp in inputs:
            result.append({
                'curso': inp.survey_id.title,
                'usuario': inp.partner_id.name if inp.partner_id else inp.email,
                'estado': inp.state,
                'fecha_inicio': str(inp.create_date.date()) if inp.create_date else None,
                'fecha_fin': str(inp.date_deadline) if inp.date_deadline else None,
            })
        return {
            'total': len(result),
            'resultados': result,
        }

    def _tool_get_project_delays(self, args, env):
        """Busca tareas de proyecto con fecha límite superada."""
        project_name = args.get('project_name', '')
        days_overdue = int(args.get('days_overdue', 0))
        today = date.today()

        domain = [
            ('date_deadline', '<', today.isoformat()),
            ('state', 'not in', ['1_done', 'cancel']),
        ]
        if project_name:
            domain.append(('project_id.name', 'ilike', project_name))

        tasks = env['project.task'].search(domain, limit=50)
        result = []
        for task in tasks:
            delta = (today - task.date_deadline).days if task.date_deadline else 0
            if delta >= days_overdue:
                result.append({
                    'tarea': task.name,
                    'proyecto': task.project_id.name if task.project_id else None,
                    'responsable': task.user_ids[0].name if task.user_ids else 'Sin asignar',
                    'fecha_limite': str(task.date_deadline),
                    'dias_retraso': delta,
                    'estado': task.state,
                })
        result.sort(key=lambda x: x['dias_retraso'], reverse=True)
        return {
            'total': len(result),
            'resultados': result,
        }

    def _tool_validate_compliance(self, args, env):
        """Verifica campos básicos de cumplimiento de RRHH para un empleado."""
        employee_name = args.get('employee_name', '')
        if not employee_name:
            return {'error': _('Se requiere el nombre del empleado.')}

        employees = env['hr.employee'].search(
            [('name', 'ilike', employee_name)], limit=5
        )
        if not employees:
            return {'error': _('No se encontró ningún empleado con el nombre: %s') % employee_name}

        result = []
        for emp in employees:
            checks = {
                'nombre': emp.name,
                'puesto': emp.job_id.name if emp.job_id else None,
                'departamento': emp.department_id.name if emp.department_id else None,
                'tiene_contrato': bool(emp.contract_id) if hasattr(emp, 'contract_id') else 'N/A',
                'fecha_ingreso': str(emp.date_start) if hasattr(emp, 'date_start') and emp.date_start else None,  # noqa
                'estado': emp.active,
            }
            result.append(checks)

        return {
            'total': len(result),
            'empleados': result,
        }
