# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from unittest.mock import patch, MagicMock


@tagged('post_install', '-at_install')
class TestExecuteSearchHelper(TransactionCase):

    def setUp(self):
        super(TestExecuteSearchHelper, self).setUp()
        self.ai_search = self.env['leulit_ai.search.engine']

    def test_hard_limit_caps_high_limit(self):
        """Un limit por encima de HARD_SEARCH_LIMIT (100) se recorta a 100."""
        with patch.object(type(self.env['res.partner']), 'search') as mock_search:
            mock_search.return_value = self.env['res.partner']
            self.ai_search._execute_search('res.partner', [], ['name'], limit=99999)
            _, kwargs = mock_search.call_args
            self.assertLessEqual(kwargs.get('limit'), 100)

    def test_invalid_domain_rejected(self):
        """Un domain que no es una lista de tuplas de 3 elementos debe rechazarse."""
        with self.assertRaises(UserError):
            self.ai_search._execute_search('res.partner', "not-a-domain", ['name'], limit=10)
        with self.assertRaises(UserError):
            self.ai_search._execute_search('res.partner', [['only', 'two']], ['name'], limit=10)

    def test_invalid_model_rejected(self):
        with self.assertRaises(UserError):
            self.ai_search._execute_search('not.a.real.model', [], ['name'], limit=10)

    def test_allowlist_blocks_disallowed_model(self):
        with self.assertRaises(UserError):
            self.ai_search._execute_search('res.partner', [], ['name'], limit=10, allowlist=['sale.order'])

    def test_allowlist_allows_listed_model(self):
        # No debe lanzar UserError por la allowlist (puede devolver 0 resultados, es igual).
        result = self.ai_search._execute_search('res.partner', [], ['name'], limit=10, allowlist=['res.partner'])
        self.assertIn('records', result)
        self.assertIn('fields', result)
        self.assertIn('count', result)


@tagged('post_install', '-at_install')
class TestProviderDispatch(TransactionCase):

    def setUp(self):
        super(TestProviderDispatch, self).setUp()
        self.ai_search = self.env['leulit_ai.search.engine']

    def test_default_provider_is_openrouter(self):
        provider = self.env['ir.config_parameter'].sudo().get_param('leulit_ai.ai_provider', 'openrouter')
        self.assertEqual(provider, 'openrouter')

    def test_process_query_dispatches_to_vertex_when_configured(self):
        self.env['ir.config_parameter'].sudo().set_param('leulit_ai.ai_provider', 'vertex_ai')
        with patch.object(type(self.ai_search), '_process_query_vertex') as mock_vertex:
            mock_vertex.return_value = {
                'provider': 'vertex_ai',
                'answer': 'ok',
                'records': [],
                'fields': [],
                'count': 0,
                'model': None,
                'multi_model': False,
            }
            self.ai_search.process_query("cualquier consulta")
            mock_vertex.assert_called_once_with("cualquier consulta")

    def test_process_query_does_not_call_vertex_when_openrouter(self):
        self.env['ir.config_parameter'].sudo().set_param('leulit_ai.ai_provider', 'openrouter')
        with patch.object(type(self.ai_search), '_process_query_vertex') as mock_vertex:
            with patch('requests.post') as mock_post:
                mock_post.return_value = MagicMock(status_code=200, json=lambda: {
                    'choices': [{'message': {'content': '{"model": "res.partner", "domain": [], "fields": ["name"], "limit": 5}'}}]
                })
                self.env['ir.config_parameter'].sudo().set_param('leulit_ai.openrouter_api_key', 'test_key')
                self.ai_search.process_query("cualquier consulta")
                mock_vertex.assert_not_called()
