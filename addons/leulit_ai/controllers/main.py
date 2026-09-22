from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime, date

_logger = logging.getLogger(__name__)

class AISearchController(http.Controller):
    
    @http.route('/leulit_ai/search', type='json', auth='user')
    def search(self, **kw):
        """Process a search query"""
        try:
            # Get query text
            query_text = None
            if 'query_text' in kw:
                query_text = kw.get('query_text')
            elif 'args' in kw and isinstance(kw.get('args'), list) and len(kw.get('args')) > 0:
                query_text = kw.get('args')[0]
            elif 'params' in kw and 'query_text' in kw.get('params', {}):
                query_text = kw.get('params').get('query_text')
                
            if not query_text:
                return {'status': 'error', 'error': 'No query text provided'}
            
            try:
                # Process the search - simplified approach
                search_engine = request.env['leulit_ai.search.engine'].create({})
                _logger.info("Starting AI universal search with query: %s", query_text)
                result = search_engine.process_query(query_text)
                
                # Process the result to make it serializable
                clean_result = self._recursive_serialize(result)
                return {'status': 'success', 'result': clean_result}
            except Exception as e:
                _logger.error("Error in search processing: %s", str(e), exc_info=True)
                return {'status': 'error', 'error': f"Search processing error: {str(e)}"}
                
        except Exception as e:
            _logger.error("Error in AI search: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    @http.route('/leulit_ai/save_favorite', type='json', auth='user')
    def save_favorite(self, **kw):
        """Save a search query as favorite"""
        try:
            query_text = None
            if 'query_text' in kw:
                query_text = kw.get('query_text')
            elif 'params' in kw and 'query_text' in kw.get('params', {}):
                query_text = kw.get('params').get('query_text')
                
            if not query_text:
                return {'status': 'error', 'error': 'No query text provided'}
            
            _logger.info("Saving search favorite: %s", query_text)
            
            # Create favorite
            favorite = request.env['leulit_ai.search.favorite'].create({
                'name': query_text,  # Use query text as name
                'query_text': query_text,
            })
            
            return {
                'status': 'success', 
                'result': {
                    'id': favorite.id,
                    'name': favorite.name,
                    'query_text': favorite.query_text,
                    'create_date': self._recursive_serialize(favorite.create_date)
                }
            }
            
        except Exception as e:
            _logger.error("Error saving search favorite: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}
        
    @http.route('/leulit_ai/get_favorites', type='json', auth='user')
    def get_favorites(self, **kw):
        """Get user's favorite searches"""
        try:
            # Get current user's favorites
            current_user = request.env.user
            favorites = request.env['leulit_ai.search.favorite'].search([
                ('user_id', '=', current_user.id)
            ], order='create_date desc')
            
            result = []
            
            for favorite in favorites:
                result.append({
                    'id': favorite.id,
                    'name': favorite.name,
                    'query_text': favorite.query_text,
                    'create_date': self._recursive_serialize(favorite.create_date)
                })
                
            return {'status': 'success', 'result': result}
            
        except Exception as e:
            _logger.error("Error getting search favorites: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}

    @http.route('/leulit_ai/delete_favorite', type='json', auth='user')
    def delete_favorite(self, **kw):
        """Delete a favorite search"""
        try:
            favorite_id = None
            if 'favorite_id' in kw:
                favorite_id = kw.get('favorite_id')
            elif 'params' in kw and 'favorite_id' in kw.get('params', {}):
                favorite_id = kw.get('params').get('favorite_id')
                
            if not favorite_id:
                return {'status': 'error', 'error': 'No favorite ID provided'}
                
            # Find the favorite
            current_user = request.env.user
            favorite = request.env['leulit_ai.search.favorite'].search([
                ('id', '=', int(favorite_id)),
                ('user_id', '=', current_user.id)
            ])
            
            if not favorite:
                return {'status': 'error', 'error': 'Favorite not found or access denied'}
                
            # Delete the favorite
            favorite.unlink()
            return {'status': 'success'}
            
        except Exception as e:
            _logger.error("Error deleting search favorite: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    # Report Management API Endpoints
    @http.route('/leulit_ai/create_report', type='json', auth='user')
    def create_report(self, name=None, query_text=None, visualization_type=None, config=None, data=None, **kw):
        """Create a new report from search results"""
        try:
            # Log the raw input for debugging
            _logger.info("Create report raw input - name: %s, query_text: %s, vis_type: %s", name, query_text, visualization_type)
            _logger.info("Create report kw: %s", kw)
            
            # If direct parameters weren't passed, try to get them from kw['params']
            if (not name or not query_text) and 'params' in kw:
                params = kw.get('params', {})
                _logger.info("Getting values from params: %s", params)
                
                if not name:
                    name = params.get('name')
                if not query_text:
                    query_text = params.get('query_text')
                if not visualization_type:
                    visualization_type = params.get('visualization_type', 'bar')
                if not config:
                    config = params.get('config', {})
                if not data:
                    data = params.get('data', {})
            
            # Force conversion to string
            if name:
                name = str(name)
            if query_text:
                query_text = str(query_text)
                
            _logger.info("Final values: name=%s, query_text=%s", name, query_text)
            
            # BYPASS VALIDATION FOR TESTING - CREATE REPORT ANYWAY
            if not name:
                name = "Unnamed Report"
                _logger.warning("Using default name because none was provided")
            if not query_text:
                query_text = "No query"
                _logger.warning("Using default query because none was provided")
            
            # Always use a default visualization type
            if not visualization_type:
                visualization_type = 'bar'
            
            # Create the report
            report = request.env['leulit_ai.search.report'].create({
                'name': name,
                'query_text': query_text,
                'visualization_type': visualization_type,
                'config': json.dumps(config),
                'data': json.dumps(data)
            })
            
            return {
                'status': 'success',
                'result': {
                    'id': report.id,
                    'name': report.name
                }
            }
            
        except Exception as e:
            _logger.error("Error creating report: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    @http.route('/leulit_ai/get_reports', type='json', auth='user')
    def get_reports(self, **kw):
        """Get user's saved reports"""
        try:
            # Get current user's reports
            current_user = request.env.user
            reports = request.env['leulit_ai.search.report'].search([
                ('user_id', '=', current_user.id)
            ], order='create_date desc')
            
            result = []
            
            for report in reports:
                # Get the data as dict 
                try:
                    data = json.loads(report.data) if report.data else {}
                except:
                    data = {}
                
                result.append({
                    'id': report.id,
                    'name': report.name,
                    'query_text': report.query_text,
                    'visualization_type': report.visualization_type,
                    'create_date': self._recursive_serialize(report.create_date),
                    'data': data  # Include the actual data for visualization
                })
                
            return {'status': 'success', 'result': result}
            
        except Exception as e:
            _logger.error("Error getting reports: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    @http.route('/leulit_ai/delete_report', type='json', auth='user')
    def delete_report(self, **kw):
        """Delete a saved report"""
        try:
            report_id = None
            if 'report_id' in kw:
                report_id = kw.get('report_id')
            elif 'params' in kw and 'report_id' in kw.get('params', {}):
                report_id = kw.get('params').get('report_id')
                
            if not report_id:
                return {'status': 'error', 'error': 'No report ID provided'}
                
            # Find the report
            current_user = request.env.user
            report = request.env['leulit_ai.search.report'].search([
                ('id', '=', int(report_id)),
                ('user_id', '=', current_user.id)
            ])
            
            if not report:
                return {'status': 'error', 'error': 'Report not found or access denied'}
                
            # Delete the report
            report.unlink()
            return {'status': 'success'}
            
        except Exception as e:
            _logger.error("Error deleting report: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}
    

    @http.route('/leulit_ai/generate_visualization', type='json', auth='user')
    def generate_visualization(self, **kw):
        """Generate visualization data from search results"""
        try:
            params = kw.get('params', {})
            
            # Get the search results - try different parameter names
            search_results = params.get('searchResults') or params.get('data')
            report_id = params.get('report_id')
            
            # If report ID is provided, fetch data from the report
            if report_id and not search_results:
                current_user = request.env.user
                report = request.env['leulit_ai.search.report'].search([
                    ('id', '=', int(report_id)),
                    ('user_id', '=', current_user.id)
                ], limit=1)
                if report:
                    try:
                        search_results = json.loads(report.data)
                    except:
                        _logger.error("Failed to parse report data from report ID %s", report_id)
                        
            visualization_type = params.get('visualizationType', 'bar')
            
            _logger.info("Generating visualization - type: %s, data: %s", 
                         visualization_type, 
                         "Available" if search_results else "Not available")
            
            if not search_results:
                return {'status': 'error', 'error': 'No search results provided'}
            
            # Process data for visualization based on visualization type
            # This is a simplified example - in practice, you would need
            # more sophisticated data transformation based on the structure
            # of search_results and the desired visualization
            
            # For now, we'll return a simple structure that GraphRenderer can use
            graph_data = {
                'labels': [],
                'datasets': []
            }
            
            # Example data processing for a simple case
            if visualization_type == 'bar' or visualization_type == 'line':
                # Process table-like data for bar/line charts
                if search_results.get('records'):
                    # Single model results
                    records = search_results.get('records', [])
                    if records and len(records) > 0:
                        # Use first string field for labels and numeric field for values
                        first_record = records[0]
                        label_field = None
                        value_field = None
                        
                        # Find suitable fields
                        for field, value in first_record.items():
                            if field not in ['id', 'has_linked_data'] and not field.endswith('_info'):
                                if label_field is None and isinstance(value, str):
                                    label_field = field
                                elif value_field is None and (isinstance(value, (int, float)) or 
                                           (isinstance(value, list) and len(value) > 0 and isinstance(value[0], (int, float)))):
                                    value_field = field
                        
                        if label_field and value_field:
                            graph_data['labels'] = [record.get(label_field, '') for record in records]
                            values = []
                            for record in records:
                                val = record.get(value_field)
                                if isinstance(val, list) and len(val) > 0:
                                    values.append(val[0])
                                else:
                                    values.append(val)
                            
                            graph_data['datasets'].append({
                                'label': value_field,
                                'data': values
                            })
            
            elif visualization_type == 'pie':
                # Process data for pie chart
                if search_results.get('records'):
                    records = search_results.get('records', [])
                    if records and len(records) > 0:
                        # Similar logic as above but for pie chart
                        first_record = records[0]
                        label_field = None
                        value_field = None
                        
                        for field, value in first_record.items():
                            if field not in ['id', 'has_linked_data'] and not field.endswith('_info'):
                                if label_field is None and isinstance(value, str):
                                    label_field = field
                                elif value_field is None and (isinstance(value, (int, float)) or 
                                           (isinstance(value, list) and len(value) > 0 and isinstance(value[0], (int, float)))):
                                    value_field = field
                        
                        if label_field and value_field:
                            graph_data['labels'] = [record.get(label_field, '') for record in records]
                            values = []
                            for record in records:
                                val = record.get(value_field)
                                if isinstance(val, list) and len(val) > 0:
                                    values.append(val[0])
                                else:
                                    values.append(val)
                            
                            graph_data['datasets'].append({
                                'data': values
                            })
            
            return {
                'status': 'success',
                'result': {
                    'graphData': graph_data,
                    'visualizationType': visualization_type
                }
            }
            
        except Exception as e:
            _logger.error("Error generating visualization: %s", str(e), exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    def _recursive_serialize(self, data):
        """Convert all complex types to simple JSON-serializable values"""
        if isinstance(data, (datetime, date)):
            return data.isoformat()
            
        elif isinstance(data, dict):
            return {k: self._recursive_serialize(v) for k, v in data.items()}
            
        elif isinstance(data, list):
            return [self._recursive_serialize(item) for item in data]
            
        elif hasattr(data, '_name') and hasattr(data, 'ids'):  # Odoo recordset
            return {"_record": data._name, "ids": data.ids}
            
        return data
