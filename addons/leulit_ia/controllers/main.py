# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

# Número máximo de rondas de herramientas para evitar bucles infinitos
MAX_TOOL_ITERATIONS = 5


class AiChatController(http.Controller):

    @http.route('/ai/chat', type='json', auth='user', methods=['POST'], csrf=False)
    def chat(self, prompt, conversation_history=None):
        """
        Endpoint principal del asistente IA.

        Recibe el prompt del usuario y el historial de conversación,
        ejecuta el loop de tool-calling con el LLM configurado y
        devuelve la respuesta final en texto natural.

        :param prompt: str — Mensaje del usuario
        :param conversation_history: list — Historial previo de mensajes
        :return: dict — {'response': str, 'history': list}
        """
        if conversation_history is None:
            conversation_history = []

        config = self._get_config()
        system_prompt = self._build_system_prompt()
        tool_definitions = request.env['ai.tool.registry'].get_tool_definitions()

        # Añadir el mensaje del usuario al historial
        conversation_history.append({'role': 'user', 'content': prompt})

        response_text = ''
        for _ in range(MAX_TOOL_ITERATIONS):
            llm_response = self._call_llm(
                messages=conversation_history,
                system=system_prompt,
                tools=tool_definitions,
                config=config,
            )

            if llm_response['type'] == 'text':
                response_text = llm_response['content']
                conversation_history.append({
                    'role': 'assistant',
                    'content': response_text,
                })
                break

            if llm_response['type'] == 'tool_use':
                tool_name = llm_response['tool_name']
                tool_input = llm_response['tool_input']

                _logger.info('IA solicita herramienta: %s con args: %s', tool_name, tool_input)

                # Añadir la solicitud de herramienta al historial
                conversation_history.append({
                    'role': 'assistant',
                    'content': llm_response.get('raw_content', ''),
                    'tool_use': {'name': tool_name, 'input': tool_input},
                })

                # Ejecutar la herramienta con el env del usuario actual (ACLs garantizadas)
                tool_result = request.env['ai.tool.registry'].execute_tool(
                    name=tool_name,
                    arguments=tool_input,
                    env=request.env,
                )

                # Añadir el resultado al historial
                conversation_history.append({
                    'role': 'tool',
                    'tool_name': tool_name,
                    'content': json.dumps(tool_result, ensure_ascii=False, default=str),
                })

        else:
            response_text = _('Lo siento, no pude completar la consulta en el número máximo de pasos.')

        return {
            'response': response_text,
            'history': conversation_history,
        }

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------

    def _get_config(self):
        """Lee los parámetros de configuración de leulit_ia."""
        ICP = request.env['ir.config_parameter'].sudo()
        return {
            'provider': ICP.get_param('leulit_ia.provider', 'claude'),
            'claude_api_key': ICP.get_param('leulit_ia.claude_api_key', ''),
            'ollama_url': ICP.get_param('leulit_ia.ollama_url', 'http://localhost:11434'),
            'ollama_model': ICP.get_param('leulit_ia.ollama_model', 'llama3'),
            'temperature': float(ICP.get_param('leulit_ia.temperature', '0.3')),
            'max_tokens': int(ICP.get_param('leulit_ia.max_tokens', '1024')),
        }

    def _build_system_prompt(self):
        """Construye el system prompt con el contexto del usuario y la fecha."""
        user = request.env.user
        now = datetime.now()
        return (
            f"Eres un asistente IA integrado en Odoo para la empresa de helipuertos Leulit. "
            f"Ayudas al equipo con consultas sobre datos de negocio: proyectos, tareas, "
            f"cursos, cumplimiento de RRHH y operaciones.\n\n"
            f"Contexto actual:\n"
            f"- Usuario: {user.name} ({user.login})\n"
            f"- Fecha y hora: {now.strftime('%d/%m/%Y %H:%M')}\n"
            f"- Idioma: Español\n\n"
            f"Instrucciones:\n"
            f"- Responde siempre en español.\n"
            f"- Usa las herramientas disponibles para obtener datos reales de Odoo. "
            f"No inventes ni asumas datos.\n"
            f"- Si no encuentras información, indícalo claramente.\n"
            f"- Formatea las respuestas con Markdown cuando sea útil (listas, tablas, negritas).\n"
            f"- No ejecutes herramientas si la pregunta es general o de conversación."
        )

    # ------------------------------------------------------------------
    # Abstracción de proveedores LLM
    # ------------------------------------------------------------------

    def _call_llm(self, messages, system, tools, config):
        """
        Llama al LLM configurado y retorna una respuesta normalizada.

        :return: dict con keys:
            - 'type': 'text' | 'tool_use'
            - 'content': str (si type='text')
            - 'tool_name': str (si type='tool_use')
            - 'tool_input': dict (si type='tool_use')
            - 'raw_content': cualquier contenido bruto del assistant
        """
        provider = config.get('provider', 'claude')
        if provider == 'claude':
            return self._call_claude(messages, system, tools, config)
        return self._call_ollama(messages, system, tools, config)

    def _call_claude(self, messages, system, tools, config):
        """Llama a la API de Anthropic Claude."""
        try:
            import anthropic
        except ImportError:
            return {
                'type': 'text',
                'content': _('Error: el paquete Python "anthropic" no está instalado en el servidor.'),
            }

        api_key = config.get('claude_api_key')
        if not api_key:
            return {
                'type': 'text',
                'content': _('Error: no hay Claude API Key configurada. '
                             'Ve a Ajustes > Leulit IA para configurarla.'),
            }

        # Normalizar historial al formato Claude (sin mensajes 'tool' en formato plano)
        claude_messages = self._normalize_messages_for_claude(messages)

        # Convertir tool definitions al formato Claude
        claude_tools = [
            {
                'name': t['name'],
                'description': t['description'],
                'input_schema': t['input_schema'],
            }
            for t in tools
        ]

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-3-5-haiku-20241022',
            max_tokens=config['max_tokens'],
            temperature=config['temperature'],
            system=system,
            messages=claude_messages,
            tools=claude_tools,
        )

        # Procesar la respuesta
        if response.stop_reason == 'tool_use':
            for block in response.content:
                if block.type == 'tool_use':
                    return {
                        'type': 'tool_use',
                        'tool_name': block.name,
                        'tool_input': block.input,
                        'raw_content': response.content,
                    }

        # Respuesta de texto
        text = ''.join(
            block.text for block in response.content
            if hasattr(block, 'text')
        )
        return {'type': 'text', 'content': text}

    def _call_ollama(self, messages, system, tools, config):
        """Llama a un servidor Ollama local."""
        import requests

        ollama_url = config.get('ollama_url', 'http://localhost:11434').rstrip('/')
        model = config.get('ollama_model', 'llama3')

        # Construir mensajes para Ollama (formato OpenAI-compatible)
        ollama_messages = [{'role': 'system', 'content': system}]
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'tool':
                ollama_messages.append({
                    'role': 'tool',
                    'content': content,
                })
            elif role in ('user', 'assistant'):
                ollama_messages.append({'role': role, 'content': content or ''})

        # Convertir tools al formato Ollama (similar a OpenAI function calling)
        ollama_tools = [
            {
                'type': 'function',
                'function': {
                    'name': t['name'],
                    'description': t['description'],
                    'parameters': t['input_schema'],
                },
            }
            for t in tools
        ]

        payload = {
            'model': model,
            'messages': ollama_messages,
            'tools': ollama_tools,
            'options': {
                'temperature': config['temperature'],
                'num_predict': config['max_tokens'],
            },
            'stream': False,
        }

        try:
            resp = requests.post(
                f'{ollama_url}/api/chat',
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.exception('Error al llamar a Ollama')
            return {'type': 'text', 'content': _('Error al conectar con Ollama: %s') % str(e)}

        message = data.get('message', {})

        # Verificar si hay tool calls
        tool_calls = message.get('tool_calls', [])
        if tool_calls:
            call = tool_calls[0]
            fn = call.get('function', {})
            return {
                'type': 'tool_use',
                'tool_name': fn.get('name', ''),
                'tool_input': fn.get('arguments', {}),
                'raw_content': message.get('content', ''),
            }

        return {'type': 'text', 'content': message.get('content', '')}

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _normalize_messages_for_claude(self, messages):
        """
        Convierte el historial interno al formato que espera la API de Claude.
        Los mensajes de tipo 'tool' se transforman en bloques tool_result.
        """
        result = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get('role')

            if role == 'user':
                result.append({'role': 'user', 'content': msg['content']})

            elif role == 'assistant':
                tool_use = msg.get('tool_use')
                if tool_use:
                    # El siguiente mensaje debería ser el resultado de la herramienta
                    tool_result_msg = messages[i + 1] if i + 1 < len(messages) else None
                    tool_result_content = tool_result_msg['content'] if tool_result_msg else ''

                    result.append({
                        'role': 'assistant',
                        'content': [
                            {
                                'type': 'tool_use',
                                'id': f"tool_{i}",
                                'name': tool_use['name'],
                                'input': tool_use['input'],
                            }
                        ],
                    })
                    result.append({
                        'role': 'user',
                        'content': [
                            {
                                'type': 'tool_result',
                                'tool_use_id': f"tool_{i}",
                                'content': tool_result_content,
                            }
                        ],
                    })
                    i += 2  # saltar el mensaje 'tool' que ya procesamos
                    continue
                else:
                    result.append({'role': 'assistant', 'content': msg.get('content', '')})

            # Los mensajes 'tool' ya se procesan junto con el assistant anterior
            i += 1

        return result
