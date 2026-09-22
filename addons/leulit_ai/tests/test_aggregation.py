from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError
from unittest.mock import patch, MagicMock
import json
import logging

_logger = logging.getLogger(__name__)

@tagged('post_install', '-at_install')
class TestAggregation(TransactionCase):
    """Test suite for the aggregation query functionality in AI Universal Search"""

    def setUp(self):
        super().setUp()
        self.search_engine = self.env['leulit_ai.search.engine']
        
        # Set the API key explicitly for tests
        self.env['ir.config_parameter'].sudo().set_param(
            'leulit_ai.openrouter_api_key', 'test_api_key'
        )
        
        # Prepare mock responses
        self.aggregation_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "aggregation": True,
                            "model": "account.move",
                            "domain": [("move_type", "in", ["out_invoice", "in_invoice"])],
                            "group_by": ["invoice_date:day"],
                            "measures": ["__count"],
                        })
                    }
                }
            ]
        }
        
        self.aggregation_invalid_field_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "aggregation": True,
                            "model": "account.move",
                            "domain": [],
                            "group_by": ["nonexistent_field:day"],
                            "measures": ["nonexistent_measure", "__count"],
                        })
                    }
                }
            ]
        }
        
    def test_aggregation_query(self):
        """Test that aggregation queries work properly"""
        # Create a sample aggregation query
        query_data = {
            "aggregation": True,
            "model": "account.move",
            "domain": [("move_type", "in", ["out_invoice", "in_invoice"])],
            "group_by": ["invoice_date:day"],
            "measures": ["__count"],
        }
        
        # Execute the query
        result = self.search_engine._execute_aggregation_query(query_data)
        
        # Verify the result structure
        self.assertTrue(result.get('aggregation'), "Result should be marked as aggregation")
        self.assertEqual(result.get('model'), "account.move", "Model should match")
        self.assertEqual(result.get('dimension'), "invoice_date", "Dimension field should be extracted")
        self.assertEqual(result.get('measure'), "count", "Measure field should be count")
        
        # Check that we have records in the result
        self.assertTrue('records' in result, "Result should contain records")
        self.assertTrue(isinstance(result['records'], list), "Records should be a list")
        
        # Log the result for manual inspection
        _logger.info("Aggregation test result: %s", result)
        
        # Verify each record has the dimension and measure fields
        for record in result.get('records', []):
            self.assertTrue('invoice_date' in record, "Each record should have the dimension field")
            self.assertTrue('count' in record, "Each record should have the measure field")
            
    @patch('requests.post')
    def test_aggregate_by_date(self, mock_post):
        """Test a complete query with natural language for date aggregation using mocked AI response"""
        # Setup the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.aggregation_response
        mock_post.return_value = mock_response
            
        # Use a query that should trigger aggregation
        result = self.search_engine.process_query("How many invoices grouped by date")
        
        # Verify the request was made with correct parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertIn('Bearer test_api_key', kwargs['headers']['Authorization'])
        self.assertIn("How many invoices grouped by date", kwargs['json']['messages'][1]['content'])
        
        # Check if the result has aggregation data
        self.assertTrue(result.get('aggregation'), "Result should be marked as aggregation")
        self.assertEqual(result.get('model'), "account.move", "Model should match")
        self.assertEqual(result.get('dimension'), "invoice_date", "Dimension field should be extracted")
    
    @patch('requests.post')
    def test_aggregation_field_validation(self, mock_post):
        """Test that invalid fields in aggregation query properly raise an error"""
        # Setup the mock response with invalid fields
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.aggregation_invalid_field_response
        mock_post.return_value = mock_response
            
        # Execute query that would cause validation to activate
        # This should raise a UserError because nonexistent_field doesn't exist
        with self.assertRaises(UserError) as context:
            result = self.search_engine.process_query("Count invoices by nonexistent field")
        
        # Make sure the error message contains the field name
        self.assertIn("nonexistent_field", str(context.exception))
        self.assertIn("does not exist", str(context.exception))
