import odoo.tests.common as common
from odoo.exceptions import UserError
import os
import unittest
import requests
import logging
from unittest.mock import patch

_logger = logging.getLogger(__name__)

# Original request sending method from requests that we'll restore in our tests
original_send = requests.Session.send

# Tag with special integration tag to allow selective running
# e.g. odoo-bin -c odoo.conf -d test_db --test-tags leulit_ia_integration
@common.tagged('post_install', '-at_install', 'leulit_ia_integration')
class TestAISearchIntegration(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestAISearchIntegration, cls).setUpClass()
        # Patch the Session.send method to allow external requests during integration tests
        # This bypasses Odoo's BlockedRequest mechanism in the test environment
        patcher = patch('requests.Session.send', original_send)
        cls.startClassPatcher(patcher)
    """
    Integration tests for AI Universal Search that make actual API calls to OpenRouter.
    
    IMPORTANT: These tests require a valid OpenRouter API key and internet connection.
    They are meant to be run selectively before releases, not in every test run.
    
    To run only these tests: 
    odoo-bin -c odoo.conf -d test_db --test-tags leulit_ia_integration
    """

    def setUp(self):
        super(TestAISearchIntegration, self).setUp()
        self.search_engine = self.env['leulit_ia.search.engine']
        
        # Try to get API key from environment variable first
        api_key_env = os.environ.get('OPENROUTER_API_KEY_TEST')
        
        # If no env var, try from Odoo config
        if not api_key_env:
            api_key_config = self.env['ir.config_parameter'].sudo().get_param('leulit_ia.openrouter_api_key')
            if api_key_config:
                _logger.info("Using API key from Odoo config for integration tests")
                # Set API key to Odoo config (make sure we have it there)
                self.env['ir.config_parameter'].sudo().set_param('leulit_ia.openrouter_api_key', api_key_config)
        else:
            _logger.info("Using API key from environment variable for integration tests")
            # Use the environment variable key
            self.env['ir.config_parameter'].sudo().set_param('leulit_ia.openrouter_api_key', api_key_env)
            
        # Get the final configured key
        self.api_key = self.env['ir.config_parameter'].sudo().get_param('leulit_ia.openrouter_api_key')
        
        # Skip all tests if no API key is found
        if not self.api_key:
            self.skipTest("OpenRouter API key not found in environment or config. Set OPENROUTER_API_KEY_TEST env var or configure in Odoo.")

    def test_01_simple_search_integration(self):
        """Test a simple query requiring a single model via real OpenRouter API."""
        try:
            _logger.info("Running simple search integration test with OpenRouter")
            query = "Show all users" 
            result = self.search_engine.process_query(query)
            
            self.assertIsNotNone(result, "Result should not be None")
            
            # It could be either a single model or multi-model response, as AI might choose either
            if not result.get('multi_model'):
                # Single model response
                self.assertIn('model', result, "Single model result should have 'model' key")
                self.assertIn('records', result, "Should have records array")
                self.assertIsInstance(result['records'], list, "Records should be a list")
                
                # Check reasonable model for user query (might be res.users or res.partner)
                model = result.get('model')
                self.assertTrue(model in ['res.users', 'res.partner'], 
                                f"Expected model to be res.users or res.partner, got {model}")
            else:
                # Multi-model response
                self.assertIn('results', result, "Multi-model result should have 'results' key")
                self.assertIsInstance(result['results'], list, "Results should be a list")
                
                # Check if there's a users model in the results
                found_users = False
                for model_result in result.get('results', []):
                    if model_result.get('model') in ['res.users', 'res.partner']:
                        found_users = True
                        break
                
                self.assertTrue(found_users, "Results should include res.users or res.partner model")
            
            _logger.info("Simple search integration test passed")
            
        except UserError as e:
            # If it's just a UserError, log it but fail the test
            # This could be due to API rate limiting, invalid key, etc.
            _logger.error("UserError in integration test_01_simple_search_integration: %s", str(e))
            raise
        except Exception as e:
            _logger.error("Exception in integration test_01_simple_search_integration: %s", str(e), exc_info=True)
            raise

    def test_02_multi_model_search_integration(self):
        """Test a query requiring multiple models via real OpenRouter API."""
        try:
            _logger.info("Running multi-model search integration test with OpenRouter")
            query = "Show users and their related partners"
            
            # Create test users for the search
            if self.env['res.users'].search_count([]) < 3:
                _logger.info("Creating test users for integration test")
                
                # Try to find or create a partner
                partner = self.env['res.partner'].create({
                    'name': 'Test Partner for Integration',
                    'email': 'test.integration@example.com',
                })
                
                # Create a user linked to this partner
                self.env['res.users'].create({
                    'name': 'Test User for Integration',
                    'login': 'test_integration_user',
                    'email': 'test.integration@example.com',
                    'partner_id': partner.id,
                })
            
            result = self.search_engine.process_query(query)
            
            self.assertIsNotNone(result, "Result should not be None")
            self.assertTrue(result.get('multi_model'), "Should be a multi-model result")
            self.assertIn('results', result, "Result should contain 'results' list")
            self.assertGreaterEqual(len(result['results']), 1, "Should have results for at least one model")
            
            # Check that we have appropriate models in the results
            models_found = set(res['model'] for res in result.get('results', []))
            self.assertTrue(
                any(model in ['res.users', 'res.partner'] for model in models_found), 
                f"Results should include users or partners models, got {models_found}"
            )
            
            _logger.info("Multi-model search integration test passed, found models: %s", models_found)
            
        except UserError as e:
            _logger.error("UserError in integration test_02_multi_model_search_integration: %s", str(e))
            raise
        except Exception as e:
            _logger.error("Exception in integration test_02_multi_model_search_integration: %s", str(e), exc_info=True)
            raise

    def test_03_aggregation_search_integration(self):
        """Test an aggregation query via real OpenRouter API."""
        try:
            _logger.info("Running aggregation search integration test with OpenRouter")
            query = "Count users by company"
            
            # Create test data if needed
            if self.env['res.users'].search_count([]) < 3:
                _logger.info("Creating test users for aggregation test")
                
                # Use existing companies
                companies = self.env['res.company'].search([], limit=2)
                if len(companies) < 2:
                    # Create a second company if needed
                    self.env['res.company'].create({
                        'name': 'Test Company for Integration',
                        'currency_id': self.env.ref('base.EUR').id,
                    })
                    companies = self.env['res.company'].search([], limit=2)
                
                # Create a user for each company
                for idx, company in enumerate(companies):
                    partner = self.env['res.partner'].create({
                        'name': f'Test Partner {idx+1} for Integration',
                        'email': f'test.integration{idx+1}@example.com',
                        'company_id': company.id,
                    })
                    
                    self.env['res.users'].create({
                        'name': f'Test User {idx+1} for Integration',
                        'login': f'test_integration_user_{idx+1}',
                        'email': f'test.integration{idx+1}@example.com',
                        'company_id': company.id,
                        'company_ids': [(6, 0, [company.id])],
                        'partner_id': partner.id,
                    })
            
            result = self.search_engine.process_query(query)
            
            self.assertIsNotNone(result, "Result should not be None")
            self.assertTrue(result.get('aggregation'), "Should be an aggregation result")
            
            # Check that we have appropriate model 
            model = result.get('model', '')
            self.assertTrue('res.users' in model or 'users' in model, 
                           f"Expected users-related model, got {model}")
            
            # Check for dimension and measure
            self.assertIn('dimension', result, "Result should have a dimension")
            self.assertIn('measure', result, "Result should have a measure")
            
            # Check that dimension is likely company-related
            dimension = result.get('dimension', '')
            self.assertTrue('company' in dimension or 'id' in dimension,
                           f"Expected company-related dimension, got {dimension}")
            
            # Should have count as measure
            self.assertEqual(result.get('measure'), 'count', "Measure should be count")
            
            _logger.info("Aggregation search integration test passed")
            
        except UserError as e:
            _logger.error("UserError in integration test_03_aggregation_search_integration: %s", str(e))
            raise
        except Exception as e:
            _logger.error("Exception in integration test_03_aggregation_search_integration: %s", str(e), exc_info=True)
            raise

    def test_04_finnish_search_integration(self):
        """Test a Finnish language query via real OpenRouter API."""
        try:
            _logger.info("Running Finnish search integration test with OpenRouter")
            query = "Montako käyttäjää on yhtiöittäin?"
            
            result = self.search_engine.process_query(query)
            
            self.assertIsNotNone(result, "Result should not be None")
            
            # This should trigger an aggregation due to "montako"
            self.assertTrue(result.get('aggregation'), "Finnish query with 'montako' should trigger aggregation")
            
            # Check for structure
            self.assertIn('model', result, "Result should contain 'model'")
            self.assertIn('dimension', result, "Result should have a dimension")
            self.assertIn('measure', result, "Result should have a measure")
            self.assertIn('records', result, "Result should contain 'records'")
            
            _logger.info("Finnish search integration test passed")
            
        except UserError as e:
            _logger.error("UserError in integration test_04_finnish_search_integration: %s", str(e))
            raise
        except Exception as e:
            _logger.error("Exception in integration test_04_finnish_search_integration: %s", str(e), exc_info=True)
            raise

    def test_05_schema_optimization_integration(self):
        """Test schema optimization with a specific query via real OpenRouter API."""
        try:
            _logger.info("Running schema optimization integration test with OpenRouter")
            
            # First get the original schema to see total model count
            original_schema = self.search_engine.get_model_schema()
            original_model_count = len(original_schema)
            
            # Test specifically with a query relevant to contacts
            query = "Find contacts in Finland"
            
            # Call the optimization directly to test it
            optimized_schema = self.search_engine._optimize_schema_for_query(original_schema, query)
            optimized_model_count = len(optimized_schema)
            
            # The optimized schema should be smaller
            self.assertLess(optimized_model_count, original_model_count, 
                           "Optimized schema should contain fewer models than the original")
            
            # And it should definitely contain res.partner
            self.assertIn('res.partner', optimized_schema, 
                         "Optimized schema for 'contacts' query should contain res.partner model")
            
            # Now test through the full process
            result = self.search_engine.process_query(query)
            
            self.assertIsNotNone(result, "Result should not be None")
            
            # It could be either a single model or multi-model response
            if not result.get('multi_model'):
                # Most likely we'd get res.partner for this query
                self.assertEqual(result.get('model'), 'res.partner', 
                               "Expected model to be res.partner for contacts query")
            
            _logger.info("Schema optimization integration test passed")
            
        except UserError as e:
            _logger.error("UserError in test_05_schema_optimization_integration: %s", str(e))
            raise
        except Exception as e:
            _logger.error("Exception in test_05_schema_optimization_integration: %s", str(e), exc_info=True)
            raise

    def test_06_field_validation_integration(self):
        """Test field validation with a complex query via real OpenRouter API."""
        try:
            _logger.info("Running field validation integration test with OpenRouter")
            
            # This query specifically mentions IP which isn't a field in res.users.log
            query = "Show me all login entries with their IP addresses and user details"
            
            result = self.search_engine.process_query(query)
            
            self.assertIsNotNone(result, "Result should not be None")
            
            # Check if it's a multi-model result (most likely)
            if result.get('multi_model') and result.get('results'):
                for model_result in result.get('results'):
                    if model_result.get('model') == 'res.users.log':
                        # Verify that there's no 'ip' field in the fields list
                        self.assertNotIn('ip', model_result.get('fields', []), 
                                       "Invalid 'ip' field should be filtered out of res.users.log")
            # Otherwise if it's a single model result for res.users.log
            elif result.get('model') == 'res.users.log':
                self.assertNotIn('ip', result.get('fields', []), 
                               "Invalid 'ip' field should be filtered out of res.users.log")
            
            _logger.info("Field validation integration test passed")
            
        except UserError as e:
            _logger.error("UserError in test_06_field_validation_integration: %s", str(e))
            raise
        except Exception as e:
            _logger.error("Exception in test_06_field_validation_integration: %s", str(e), exc_info=True)
            raise
