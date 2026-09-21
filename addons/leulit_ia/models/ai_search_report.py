from odoo import api, fields, models
import json

class AISearchReport(models.Model):
    _name = 'leulit_ia.search.report'
    _description = 'AI Search Report'
    
    name = fields.Char(string='Name', required=True)
    query_text = fields.Text(string='Query Text', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    visualization_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart')
    ], string='Visualization Type', default='bar', required=True)
    
    # Visualization configuration stored as JSON
    config = fields.Text(string='Configuration', default="{}")
    
    # Search results data stored as JSON for visualization
    data = fields.Text(string='Data', default="{}")
    
    # Timestamp
    create_date = fields.Datetime(string='Created On', readonly=True)
    
    def get_config_dict(self):
        """Parse and return the configuration as a dictionary"""
        try:
            return json.loads(self.config)
        except (ValueError, TypeError):
            return {}
            
    def get_data_dict(self):
        """Parse and return the data as a dictionary"""
        try:
            return json.loads(self.data)
        except (ValueError, TypeError):
            return {}
