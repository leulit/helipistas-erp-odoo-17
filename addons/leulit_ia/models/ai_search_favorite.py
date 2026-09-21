from odoo import models, fields, api, _

class AISearchFavorite(models.Model):
    """
    Model for storing user's favorite search queries.
    This allows users to save and reuse common searches.
    """
    _name = 'leulit_ia.search.favorite'
    _description = 'AI Search Favorite'
    _order = 'create_date desc'
    
    name = fields.Char(string='Name', required=True)
    query_text = fields.Char(string='Query Text', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id, required=True)
    create_date = fields.Datetime(string='Created On', readonly=True)
    
    def execute_search(self):
        """Execute the saved search query"""
        self.ensure_one()
        search_engine = self.env['leulit_ia.search.engine'].create({})
        return search_engine.process_query(self.query_text)
