# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from unittest.mock import patch, MagicMock
import json

@tagged('post_install', '-at_install')
class TestAIUniversalSearch(TransactionCase):
    
    def setUp(self):
        super(TestAIUniversalSearch, self).setUp()
        # Create test users for search tests
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test@example.com',
        })
        
        # Create the search engine object once for all tests
        self.ai_search = self.env['leulit_ia.search.engine']
        
        # Set the API key explicitly for tests
        self.env['ir.config_parameter'].sudo().set_param(
            'leulit_ia.openrouter_api_key', 'test_api_key'
        )
        
        # Prepare mock responses
        self.single_model_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "model": "res.users",
                            "domain": [],
                            "fields": ["name", "login", "email"],
                            "limit": 20
                        })
                    }
                }
            ]
        }
        
        self.multi_model_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "multi_model": True,
                            "queries": [
                                {
                                    "model": "res.users.log",
                                    "domain": [],
                                    "fields": ["create_date", "create_uid"],
                                    "limit": 20
                                },
                                {
                                    "model": "res.users",
                                    "domain": [],
                                    "fields": ["name", "login", "email"],
                                    "limit": 20
                                }
                            ]
                        })
                    }
                }
            ]
        }
        
        self.invalid_field_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "model": "res.users.log",
                            "domain": [],
                            "fields": ["create_date", "create_uid", "ip", "nonexistent_field"],
                            "limit": 20
                        })
                    }
                }
            ]
        }
        
        self.error_response = {
            "error": {
                "message": "Test error message from API"
            }
        }
        
        self.empty_choices_response = {
            "choices": []
        }
    
    @patch('requests.post')
    def test_simple_user_search(self, mock_post):
        """Test searching for users with mocked AI response."""
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.single_model_response
        mock_post.return_value = mock_response
        
        # Test the 'list users' query
        result = self.ai_search.process_query("listaa käyttäjät")
        
        # Verify the request was made with correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertIn('Bearer test_api_key', kwargs['headers']['Authorization'])
        self.assertIn("listaa käyttäjät", kwargs['json']['messages'][1]['content'])
        # Validate structure matches what frontend expects
        self.assertIsInstance(result, dict, "Result should be a dictionary")
        if result.get('multi_model'):
            # Multi-model result case
            self.assertIn('results', result, "Multi-model result should have 'results' key")
            self.assertIsInstance(result['results'], list, "Results should be a list")
            self.assertIn('total_count', result, "Should have total_count field")
        else:
            # Single model result case
            self.assertIn('model', result, "Single-model result should have 'model' key")
            self.assertIn('records', result, "Should have records array")
            self.assertIsInstance(result['records'], list, "Records should be a list")
            self.assertIn('fields', result, "Should have fields array")
            
        # Verify we got user data
        if not result.get('multi_model'):
            self.assertEqual(result.get('model'), 'res.users', "Model should be res.users")
            self.assertTrue(len(result.get('records', [])) > 0, "Should find at least one user")

    @patch('requests.post')
    def test_cross_model_search(self, mock_post):
        """Test cross-model search functionality with mocked AI response."""
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.multi_model_response
        mock_post.return_value = mock_response
        
        # Create test auth log
        self.env['res.users.log'].create({
            'create_uid': self.test_user.id,
        })
        
        # Test the 'join logins with user info' query
        result = self.ai_search.process_query("yhdistä sisäänkirjautumiset käyttäjän tietoihin")
    @patch('requests.post')
    def test_field_validation(self, mock_post):
        """Test that invalid fields are properly filtered out."""
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.invalid_field_response
        mock_post.return_value = mock_response
        
        # Execute the query
        result = self.ai_search.process_query("listaa kirjautumiset")
        
        # Validate results
        self.assertIsInstance(result, dict, "Result should be a dictionary")
        self.assertIn('model', result, "Result should contain the model key")
        self.assertEqual(result['model'], 'res.users.log', "Model should be res.users.log")
        self.assertIn('fields', result, "Result should contain fields")
        
        # Most important check: 'ip' and 'nonexistent_field' should NOT be in the fields
        # because they were filtered out during validation
        self.assertNotIn('ip', result['fields'], "Invalid field 'ip' should be filtered out")
        self.assertNotIn('nonexistent_field', result['fields'], "Invalid field should be filtered out")
        self.assertIn('create_date', result['fields'], "Valid field should be included")
        self.assertIn('create_uid', result['fields'], "Valid field should be included")
        
    @patch('requests.post')
    def test_api_error_handling(self, mock_post):
        """Test handling of API errors."""
        # Setup the mock to return an error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.error_response
        mock_post.return_value = mock_response
        
        # Attempt to process a query, should raise UserError
        with self.assertRaises(UserError) as context:
            self.ai_search.process_query("this will fail")
        
        # Verify error message contains our test error
        self.assertIn("Test error message", str(context.exception))
        
    @patch('requests.post')
    def test_empty_ai_response(self, mock_post):
        """Test the fallback mechanism when AI returns empty choices."""
        # Setup mock to return empty choices
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.empty_choices_response
        mock_post.return_value = mock_response
        
        # Process a query - this should trigger the fallback mechanism
        result = self.ai_search.process_query("listaa käyttäjät")
        
        # The result should not be empty as the fallback mechanism should have kicked in
        self.assertIsInstance(result, dict, "Result should be a dictionary")
        self.assertIn('model', result, "Should contain a model key") 
        
        # Further validate that we got some records back through the fallback
        if 'records' in result:
            self.assertIsInstance(result['records'], list, "Records should be a list")
            
        # Alternatively, check if it's a multi-model result
        elif 'multi_model' in result and result['multi_model']:
            self.assertIn('results', result, "Multi-model should have results")
