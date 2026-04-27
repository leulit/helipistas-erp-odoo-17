# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ia_provider = fields.Selection(
        selection=[('claude', 'Claude API (Anthropic)'), ('ollama', 'Ollama (local)')],
        string='Proveedor IA',
        default='claude',
        config_parameter='leulit_ia.provider',
        help='Proveedor del modelo de lenguaje a utilizar.',
    )
    ia_claude_api_key = fields.Char(
        string='Claude API Key',
        config_parameter='leulit_ia.claude_api_key',
        help='API Key de Anthropic. Obtén una en https://console.anthropic.com/',
    )
    ia_ollama_url = fields.Char(
        string='URL Ollama',
        default='http://localhost:11434',
        config_parameter='leulit_ia.ollama_url',
        help='URL base del servidor Ollama (ej: http://localhost:11434).',
    )
    ia_ollama_model = fields.Char(
        string='Modelo Ollama',
        default='llama3',
        config_parameter='leulit_ia.ollama_model',
        help='Nombre del modelo a usar en Ollama (ej: llama3, mistral).',
    )
    ia_temperature = fields.Float(
        string='Temperatura',
        default=0.3,
        config_parameter='leulit_ia.temperature',
        help='Controla la aleatoriedad de las respuestas (0.0 = determinista, 1.0 = creativo).',
    )
    ia_max_tokens = fields.Integer(
        string='Máx. tokens de respuesta',
        default=1024,
        config_parameter='leulit_ia.max_tokens',
        help='Límite de tokens en la respuesta del modelo.',
    )

    def action_test_ia_connection(self):
        """Prueba la conexión con el proveedor IA configurado."""
        self.ensure_one()
        provider = self.ia_provider or self.env['ir.config_parameter'].sudo().get_param(
            'leulit_ia.provider', 'claude'
        )

        try:
            if provider == 'claude':
                self._test_claude_connection()
            else:
                self._test_ollama_connection()
        except UserError:
            raise
        except Exception as e:
            raise UserError(_('Error de conexión: %s') % str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('¡Conexión exitosa!'),
                'message': _('La conexión con el proveedor IA funciona correctamente.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def _test_claude_connection(self):
        api_key = self.ia_claude_api_key or self.env['ir.config_parameter'].sudo().get_param(
            'leulit_ia.claude_api_key'
        )
        if not api_key:
            raise UserError(_('Por favor, ingrese una Claude API Key.'))
        try:
            import anthropic
        except ImportError:
            raise UserError(_('El paquete Python "anthropic" no está instalado en el servidor.'))

        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model='claude-3-haiku-20240307',
            max_tokens=10,
            messages=[{'role': 'user', 'content': 'ping'}],
        )

    def _test_ollama_connection(self):
        import requests
        url = self.ia_ollama_url or self.env['ir.config_parameter'].sudo().get_param(
            'leulit_ia.ollama_url', 'http://localhost:11434'
        )
        if not url:
            raise UserError(_('Por favor, ingrese la URL del servidor Ollama.'))
        try:
            resp = requests.get(url.rstrip('/') + '/api/tags', timeout=5)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise UserError(_('No se puede conectar con Ollama en %s') % url)
        except requests.exceptions.Timeout:
            raise UserError(_('Timeout al conectar con Ollama en %s') % url)
        except Exception as e:
            raise UserError(_('Error al conectar con Ollama: %s') % str(e))
