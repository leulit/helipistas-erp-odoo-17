from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import requests
import json
import re
import os

try:
    import vertexai
    from vertexai.generative_models import (
        GenerativeModel,
        FunctionDeclaration,
        Tool,
        AutomaticFunctionCallingResponder,
    )
    from google.oauth2 import service_account
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

_logger = logging.getLogger(__name__)

HARD_SEARCH_LIMIT = 100
VERTEX_MAX_FUNCTION_CALLS = 5
VERTEX_DEFAULT_MODEL = 'gemini-1.5-flash'
VERTEX_SERVICE_ACCOUNT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vertex_service_account.json')

class AISearchEngine(models.Model):
    """
    AI-powered universal search engine that dynamically discovers and queries Odoo models
    based on natural language input.
    
    This engine leverages AI to understand natural language queries, determine which models
    and fields are relevant to the query, and execute the appropriate ORM operations - all
    without any hardcoded model names or relationships.
    """
    _name = 'leulit_ai.search.engine'
    _description = 'AI Universal Search Engine'
    
    def get_model_schema(self):
        """
        Dynamically discover all accessible models and their fields to create a comprehensive 
        schema that the AI can use to understand the data structure.
        
        This method is fully dynamic and doesn't hardcode any model names - instead it:
        1. Discovers all installed models via the ir.model table
        2. Filters out technical models for non-admin users
        3. Excludes common audit fields to reduce schema size
        4. Captures relationship information between models
        
        Returns:
            dict: A complete schema of all models and their fields
        """
        schema = {}
        
        # Get installed models, without hardcoding any specific models
        models = self.env['ir.model'].search([])
        
        # Skip technical models for non-admin users
        for model in models:
            if not self.env.user.has_group('base.group_system') and model.model.startswith('ir.'):
                continue
                
            # Get fields but exclude common audit fields to reduce schema size
            fields = self.env['ir.model.fields'].search([
                ('model_id', '=', model.id),
                ('name', 'not in', ['create_uid', 'create_date', 'write_uid', 'write_date', '__last_update'])
            ])
            
            # Build the schema dynamically
            schema[model.model] = {
                'name': model.name,
                'fields': {field.name: {
                    'type': field.ttype,
                    'string': field.field_description,
                    'relation': field.relation if field.ttype in ('many2one', 'one2many', 'many2many') else False
                } for field in fields}
            }
        
        return schema
    
    def _optimize_schema_for_query(self, schema, query_text):
        """
        Intelligent schema optimization to reduce context size while maintaining
        relevance to the user's query. Prioritizes models that might be related
        to the query without hardcoding any specific models.
        
        Args:
            schema (dict): The full schema of all models
            query_text (str): The user's natural language query
            
        Returns:
            dict: Optimized schema focused on potentially relevant models
        """
        if not query_text or len(schema) <= 20:
            return schema  # For short queries or small schemas, use the full schema
            
        # Convert query to lowercase for matching
        query_lower = query_text.lower()
            
        # Calculate relevance score for each model based on text matching
        # We avoid hardcoding by looking for matches in model names and field descriptions
        model_scores = {}
        
        for model_name, model_info in schema.items():
            score = 0
            
            # Check if model name or translated name appears in query
            model_parts = model_name.split('.')
            for part in model_parts:
                if part in query_lower:
                    score += 10
                    
            if model_info['name'].lower() in query_lower:
                score += 15
                
            # Check field names and descriptions for relevance
            for field_name, field_info in model_info['fields'].items():
                if field_name in query_lower:
                    score += 5
                if field_info['string'].lower() in query_lower:
                    score += 3
                    
            model_scores[model_name] = score
            
        # Always include base models (they're small and often needed)
        base_models = ['res.users', 'res.partner', 'res.company']
        
        # Select top scoring models + base models
        top_model_count = min(30, len(schema) // 2)  # Select either 30 or half of available models
        top_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)[:top_model_count]
        top_model_names = [m[0] for m in top_models] + base_models
        
        # Build optimized schema with only relevant models
        optimized_schema = {model: schema[model] for model in top_model_names if model in schema}
        
        return optimized_schema
    
    def process_query(self, query_text):
        """
        Process a natural language query by:
        1. Dynamically generating a schema of available models
        2. Optimizing the schema to focus on relevant models for the query
        3. Sending the query to an AI service to translate it into ORM operations
        4. Executing the resulting query and returning structured results
        
        This function contains zero hardcoded models - all models and relationships
        are discovered dynamically at runtime.
        
        Args:
            query_text (str): Natural language query from the user
            
        Returns:
            dict: Structured results from executing the query
        """
        # Import translation function to ensure it's available in this scope
        from odoo import _

        provider = self.env['ir.config_parameter'].sudo().get_param('leulit_ai.ai_provider', 'openrouter')
        if provider == 'vertex_ai':
            return self._process_query_vertex(query_text)

        # Get complete schema of all available models
        full_schema = self.get_model_schema()
        
        # Optimize schema to focus on models relevant to this query
        # This reduces context size without hardcoding specific models
        schema = self._optimize_schema_for_query(full_schema, query_text)
        
        # Get API key from Odoo settings
        api_key = self.env['ir.config_parameter'].sudo().get_param('leulit_ai.openrouter_api_key')
        
        if not api_key:
            raise UserError(_("OpenRouter API key is not configured. Please set it in the settings."))
        
        # Use Claude 3.7 Sonnet model
        model_name = "anthropic/claude-3.7-sonnet"

        # Set max_tokens to reduce context length issues
        max_tokens = 4000
        
        # Create comprehensive system prompt with escaped curly braces
        # to avoid f-string format specifier errors
        system_prompt = f"""You are an Odoo query expert. You translate natural language into Odoo ORM queries.
Here's the schema of available models: {json.dumps(schema)}

You MUST respond with a valid JSON object. 

CRITICAL RULE: ALWAYS use multi-model format when:
1. The query asks to combine information from different tables
2. The query mentions related data like "user details" along with other data
3. The query wants to see data together or linked
4. The query uses words like "yhdistä" (combine/join), "näytä" (show) with multiple types of data
5. The query includes phrases like "kirjautumishetki ja käyttäjästä"

CRITICAL RULE: ALWAYS use aggregation format when:
1. The query is asking for counts, sums, averages, or other aggregations
2. The query asks to group data by any field or time period
3. The query is analytical in nature (how many, total amount, etc.)
4. The query contains words related to data analysis in any language
5. The query's intent is to see data organized by categories or time periods
6. The query is asking to view frequency, distribution, or trends
7. Whenever the natural meaning of the query suggests summarizing data rather than viewing individual records
8. The query is specifically about "login entries" or "login events" organized by time
9. The query includes words like "montako" (how many) or "kuinka monta" (how many)

CRITICAL RULE: Every aggregation query MUST include at least one field in the group_by array:
- The group_by array MUST NEVER be empty
- If query doesn't specify a grouping field, select the most appropriate field:
  * For "how many X" queries, use the most meaningful categorical field (e.g., state, type, category)
  * For "total X" queries, use a date field with month granularity if available
  * If no other meaningful field exists, use "id" as the group_by field

For simple queries targeting a single model, use this format:
{{
  "model": "res.partner",
  "domain": [["is_company", "=", true], ["country_id.code", "=", "US"]],
  "fields": ["name", "email", "phone"],
  "limit": 10
}}

For queries that require data from MULTIPLE models, use this format:
{{
  "multi_model": true,
  "queries": [
    {{
      "model": "res.users.log",
      "domain": [],
      "fields": ["create_date", "create_uid"],
      "limit": 50
    }},
    {{
      "model": "res.users",
      "domain": [],
      "fields": ["name", "email", "login", "company_id", "phone", "active"],
      "limit": 50
    }}
  ]
}}

For queries that require AGGREGATION or GROUP BY operations, use this format:
{{
  "aggregation": true,
  "model": "account.move",
  "domain": [],
  "group_by": ["invoice_date:day"],
  "measures": ["__count"],
  "limit": 100
}}

NEVER use dot notation like "create_uid.name" - instead, always use multi-model format when you need related data!

For date-based grouping, use the field:granularity syntax (field:day, field:month, field:year) depending on the needed granularity.

The current query appears to be in Finnish. If it mentions "ryhmittele" (group by), "montako" (how many), or similar analytical terms, you MUST use the aggregation format!
"""
        
        # Prepare payload for OpenRouter API
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Convert this question to a safe Odoo ORM query: {query_text}"}
            ],
            "max_tokens": max_tokens  # Set max output tokens to help prevent context overflow
        }
        
        # Log the request for debugging
        _logger.info("AI search request: model=%s, query=%s", model_name, query_text)
        
        try:
            # Call OpenRouter API
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                _logger.error("OpenRouter API error: %s", response.text)
                raise UserError(_("AI service error: %s") % response.text)
                
            # Log the raw response
            result = response.json()
            _logger.info("OpenRouter API response: %s", json.dumps(result))
            
            # Check for error in the response
            if 'error' in result:
                error_msg = result.get('error', {}).get('message', 'Unknown API error')
                _logger.error("API returned error: %s", error_msg)
                
                # Specific handling for context length errors
                if 'exceed context limit' in error_msg:
                    raise UserError(_("The search query is too complex for the AI model. Please try a simpler query or contact your administrator to configure a model with larger context window."))
                else:
                    raise UserError(_("AI service error: %s") % error_msg)
                    
            # Only try to access 'choices' if no error was returned
            if 'choices' not in result:
                _logger.error("API response missing 'choices' field: %s", json.dumps(result))
                raise UserError(_("Invalid response from AI service. Please try again later."))
            
            # Check if choices array is empty
            if len(result['choices']) == 0:
                _logger.error("API returned empty choices array: %s", json.dumps(result))
                
                # Dynamic fallback mechanism - no hardcoded models
                _logger.info("Creating dynamic fallback query based on query content: %s", query_text)
                
                # Get all available models
                all_models = self.env['ir.model'].search([])
                
                # Calculate model relevance scores using the same algorithm as _optimize_schema_for_query
                query_lower = query_text.lower()
                model_scores = {}
                relationship_info = {}  # Track potential model relationships
                
                # Analyze all available models to find relevant ones
                for model in all_models:
                    # Skip technical models for non-admin users
                    if not self.env.user.has_group('base.group_system') and model.model.startswith('ir.'):
                        continue
                    
                    score = 0
                    model_name_lower = model.name.lower()
                    model_tech_name = model.model.lower()
                    
                    # Check if model name appears in query
                    model_parts = model_tech_name.split('.')
                    for part in model_parts:
                        # Check for direct word matches
                        for word in query_lower.split():
                            # Exact match gets higher score
                            if word == part:
                                score += 15
                            # Partial match gets lower score
                            elif word in part or part in word:
                                score += 5
                    
                    # Check translated name
                    for word in query_lower.split():
                        if word in model_name_lower:
                            score += 10
                    
                    # Special language detection (without hardcoding model names)
                    # Finnish common words
                    if 'käyttäjät' in query_lower and ('user' in model_name_lower or 'user' in model_tech_name):
                        score += 20
                    if 'kirjautumiset' in query_lower and ('log' in model_name_lower or 'log' in model_tech_name):
                        score += 20
                    
                    # Track model for potential multi-model query
                    if score > 0:
                        model_scores[model.model] = score
                        
                        # Check fields for relationship potential
                        fields = self.env['ir.model.fields'].search([
                            ('model_id', '=', model.id),
                            ('ttype', 'in', ['many2one', 'one2many', 'many2many'])
                        ])
                        
                        for field in fields:
                            if field.relation:
                                if field.relation not in relationship_info:
                                    relationship_info[field.relation] = []
                                relationship_info[field.relation].append({
                                    'from_model': model.model,
                                    'field_name': field.name,
                                    'relation_type': field.ttype
                                })
                
                # Sort models by relevance score
                sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)
                
                if not sorted_models:
                    # If no models matched, use a few common base models without hardcoding specific business logic
                    base_models = self.env['ir.model'].search([
                        ('model', 'in', ['res.partner', 'res.users', 'res.company'])
                    ], limit=1)
                    
                    if base_models:
                        sorted_models = [(base_models[0].model, 1)]
                
                # Decide whether to create a multi-model or single-model query
                should_be_multi_model = False
                if len(sorted_models) >= 2:
                    # Check if top models have relationships between them
                    top_models = [m[0] for m in sorted_models[:3]]
                    for model in top_models:
                        if model in relationship_info:
                            related_models = [r['from_model'] for r in relationship_info[model]]
                            if any(rm in top_models for rm in related_models):
                                should_be_multi_model = True
                                break
                
                # Check for linguistic hints of multi-model intent
                multi_model_indicators = [
                    'join', 'combine', 'together', 'related', 'yhdistä', 'näytä', 'ja',
                    'from', 'with', 'both', 'kanssa', 'sekä'
                ]
                
                for indicator in multi_model_indicators:
                    if indicator in query_lower:
                        should_be_multi_model = True
                        break
                
                # Check for aggregation indicators
                aggregation_indicators = [
                    'count', 'sum', 'average', 'group', 'montako', 'ryhmittele', 
                    'kuinka monta', 'total'
                ]
                
                is_aggregation = False
                for indicator in aggregation_indicators:
                    if indicator in query_lower:
                        is_aggregation = True
                        break
                
                if is_aggregation and sorted_models:
                    # Create dynamic aggregation query
                    top_model = sorted_models[0][0]
                    try:
                        _logger.info("Creating dynamic aggregation fallback for model: %s", top_model)
                        
                        # Get fields to find potential date or groupable fields
                        model_obj = self.env[top_model]
                        fields_info = model_obj.fields_get()
                        available_fields = list(fields_info.keys())
                        
                        # Find date fields for grouping
                        date_fields = []
                        for field, info in fields_info.items():
                            if info.get('type') in ('date', 'datetime'):
                                date_fields.append(field)
                        
                        # Find other groupable fields
                        groupable_fields = []
                        for field, info in fields_info.items():
                            if info.get('type') in ('many2one', 'selection'):
                                groupable_fields.append(field)
                        
                        # Choose group by field - prefer date fields
                        group_by = []
                        if date_fields:
                            # Add granularity for date fields
                            group_by = [f"{date_fields[0]}:month"]
                        elif groupable_fields:
                            group_by = [groupable_fields[0]]
                        else:
                            # Fallback to id or name if available
                            for field in ['name', 'id']:
                                if field in available_fields:
                                    group_by = [field]
                                    break
                        
                        if not group_by:
                            # If we couldn't find any group_by field, switch to non-aggregation
                            is_aggregation = False
                        else:
                            # Create aggregation query
                            fallback_query = {
                                "aggregation": True,
                                "model": top_model,
                                "domain": [],
                                "group_by": group_by,
                                "measures": ["__count"],
                                "limit": 100
                            }
                            _logger.info("Using dynamic aggregation fallback query: %s", json.dumps(fallback_query))
                            return self.execute_query(fallback_query)
                    except Exception as e:
                        _logger.error("Error creating aggregation fallback: %s", str(e))
                        # Continue to try non-aggregation fallback
                        is_aggregation = False
                
                if should_be_multi_model and len(sorted_models) >= 2:
                    # Create multi-model query with top matching models
                    _logger.info("Creating dynamic multi-model fallback")
                    
                    queries = []
                    # Use top 2-3 models
                    for model_name, _ in sorted_models[:min(3, len(sorted_models))]:
                        model_obj = self.env[model_name]
                        fields_info = model_obj.fields_get()
                        available_fields = list(fields_info.keys())
                        
                        # Dynamically select useful fields
                        selected_fields = []
                        
                        # First try common important fields
                        for field in available_fields:
                            field_info = fields_info.get(field, {})
                            # Include basic identification fields and foreign keys
                            if (field in ['name', 'display_name'] or 
                                    field_info.get('type') in ('many2one', 'char') or
                                    'id' in field.lower()):
                                selected_fields.append(field)
                            # Include all *_id fields as they are usually important relations
                            elif field.endswith('_id') and field_info.get('type') == 'many2one':
                                selected_fields.append(field)
                            
                            # Limit to reasonable number of fields
                            if len(selected_fields) >= 5:
                                break
                            
                        # If no fields were selected, use 'display_name' or name-like fields
                        if not selected_fields:
                            for field in available_fields:
                                if field == 'display_name' or 'name' in field.lower():
                                    selected_fields.append(field)
                                    break
                            
                            # If still no fields, add the first few non-technical fields
                            if not selected_fields:
                                for field in available_fields:
                                    if not field.startswith('_') and field not in ['id', 'write_uid', 'create_uid']:
                                        selected_fields.append(field)
                                        if len(selected_fields) >= 3:
                                            break
                        
                        # Default to display_name if nothing else worked
                        if not selected_fields and 'display_name' in available_fields:
                            selected_fields = ['display_name']
                        elif not selected_fields:
                            selected_fields = [available_fields[0]]  # Just use first field
                        
                        # Add to queries
                        queries.append({
                            "model": model_name,
                            "domain": [],
                            "fields": selected_fields,
                            "limit": 20
                        })
                    
                    if queries:
                        fallback_query = {
                            "multi_model": True,
                            "queries": queries
                        }
                        _logger.info("Using dynamic multi-model fallback query: %s", json.dumps(fallback_query))
                        return self.execute_query(fallback_query)
                
                # Single model fallback (when multi-model not needed or not enough relevant models)
                if sorted_models:
                    best_model = sorted_models[0][0]
                    _logger.info("Creating dynamic single-model fallback for model: %s", best_model)
                    
                    # Get field information for this model
                    model_obj = self.env[best_model]
                    fields_info = model_obj.fields_get()
                    available_fields = list(fields_info.keys())
                    
                    # Dynamically select useful fields
                    selected_fields = []
                    
                    # Build selected fields based on field type and common importance
                    for field, info in fields_info.items():
                        # Skip technical fields
                        if field.startswith('_') or field in ['write_uid', 'write_date']:
                            continue
                            
                        # Include fields by type
                        field_type = info.get('type')
                        if field_type in ('char', 'text'):
                            selected_fields.append(field)
                        elif field in ['name', 'display_name', 'email', 'phone', 'date']:
                            selected_fields.append(field)
                        elif field_type == 'many2one' and field.endswith('_id'):
                            selected_fields.append(field)
                        elif field_type in ('date', 'datetime'):
                            selected_fields.append(field)
                        
                        # Limit to reasonable number to avoid performance issues
                        if len(selected_fields) >= 6:
                            break
                    
                    # Ensure we have at least some fields
                    if not selected_fields:
                        for field in ['name', 'display_name']:
                            if field in available_fields:
                                selected_fields.append(field)
                                break
                                
                        # If still empty, add first few non-technical fields
                        if not selected_fields:
                            for field in available_fields:
                                if not field.startswith('_') and field not in ['id', 'write_uid', 'create_uid']:
                                    selected_fields.append(field)
                                    if len(selected_fields) >= 3:
                                        break
                    
                    # Create the fallback query
                    fallback_query = {
                        "model": best_model,
                        "domain": [],
                        "fields": selected_fields,
                        "limit": 20
                    }
                    _logger.info("Using dynamic single-model fallback query: %s", json.dumps(fallback_query))
                    return self.execute_query(fallback_query)
                
                # If no fallback worked, raise a user-friendly error
                raise UserError(_("The AI service returned an empty response. This could be due to rate limiting or the complexity of your query. Please try a simpler query or try again later."))
                
            # Get the content from the response
            content = result['choices'][0]['message']['content']
            _logger.info("Raw content: %s", content)
            
            # Parse the JSON response - Claude often includes explanation text with the JSON
            query_data = self._extract_json_from_ai_response(content)
            
        except requests.RequestException as e:
            _logger.exception("Network error in AI search process: %s", str(e))
            raise UserError(_("Network error connecting to AI service: %s") % str(e))
        except UserError:
            # Re-raise UserError exceptions as they already have the formatted message
            raise
        except Exception as e:
            _logger.exception("Error in AI search process: %s", str(e))
            raise UserError(_("Error processing query: %s") % str(e))
        
        # Execute the generated ORM query
        return self.execute_query(query_data)
    
    def _process_query_vertex(self, query_text):
        from odoo import _
        if not VERTEX_AI_AVAILABLE:
            raise UserError(_("The google-cloud-aiplatform package is not installed on this server."))

        params = self.env['ir.config_parameter'].sudo()
        project_id = params.get_param('leulit_ai.vertex_project_id')
        region = params.get_param('leulit_ai.vertex_region') or 'europe-west4'
        allowed_raw = params.get_param('leulit_ai.vertex_allowed_models') or ''
        allowlist = [m.strip() for m in allowed_raw.split(',') if m.strip()]

        if not project_id:
            raise UserError(_("Vertex AI Project ID is not configured. Please set it in the settings."))
        if not os.path.exists(VERTEX_SERVICE_ACCOUNT_PATH):
            raise UserError(_("Vertex AI credentials file not found. Contact your administrator."))
        if not allowlist:
            raise UserError(_("No Odoo models are allowed for Vertex AI queries. Configure the allowed models list in settings."))

        credentials = service_account.Credentials.from_service_account_file(VERTEX_SERVICE_ACCOUNT_PATH)
        vertexai.init(project=project_id, location=region, credentials=credentials)

        last_result = []

        def get_models():
            """Returns the list of Odoo models the AI is allowed to query, with their human-readable names."""
            result = []
            for m in allowlist:
                model_info = self.env['ir.model'].search([('model', '=', m)], limit=1)
                if model_info:
                    result.append({'model': m, 'name': model_info.name})
            return {'models': result}

        def get_schema(model_name: str):
            """Returns the available fields (name, type, string, relation) of one allowed Odoo model.

            Args:
                model_name: Technical name of the Odoo model, e.g. 'res.partner'.
            """
            if model_name not in allowlist:
                raise UserError(_("Model '%s' is not in the allowed list.") % model_name)
            field_recs = self.env['ir.model.fields'].search([
                ('model', '=', model_name),
                ('name', 'not in', ['create_uid', 'create_date', 'write_uid', 'write_date', '__last_update']),
            ])
            fields_schema = {
                f.name: {
                    'type': f.ttype,
                    'string': f.field_description,
                    'relation': f.relation if f.ttype in ('many2one', 'one2many', 'many2many') else False,
                }
                for f in field_recs
            }
            return {'fields': fields_schema}

        def search_odoo(model_name: str, domain: list, fields: list = None, limit: int = 20):
            """Searches records of an allowed Odoo model and returns them.

            Args:
                model_name: Technical name of the Odoo model to search, e.g. 'sale.order'.
                domain: Odoo search domain as a list of [field, operator, value] triples.
                fields: List of field names to return. Defaults to display_name if omitted.
                limit: Maximum number of records to return (capped server-side regardless of value).
            """
            search_result = self._execute_search(model_name, domain, fields, limit, allowlist=allowlist)
            last_result.append({'model_name': model_name, **search_result})
            return search_result

        def search_odoo_aggregate(model_name: str, domain: list, group_by: list, measures: list = None, limit: int = 100):
            """Runs a group-by/aggregation query (count, sum, etc.) on an allowed Odoo model.

            Args:
                model_name: Technical name of the Odoo model to aggregate, e.g. 'account.move'.
                domain: Odoo search domain as a list of [field, operator, value] triples.
                group_by: List of fields to group by, e.g. ['state'] or ['invoice_date:month'].
                measures: List of numeric fields to aggregate, or ['__count'] for a plain count.
                limit: Maximum number of groups to return (capped server-side regardless of value).
            """
            if model_name not in allowlist:
                raise UserError(_("Model '%s' is not in the allowed list.") % model_name)
            limit = min(int(limit), HARD_SEARCH_LIMIT) if limit else HARD_SEARCH_LIMIT
            agg_result = self._execute_aggregation_query({
                'model': model_name,
                'domain': domain,
                'group_by': group_by,
                'measures': measures or ['__count'],
                'limit': limit,
            })
            last_result.append({'model_name': model_name, 'records': agg_result['records'], 'fields': agg_result['fields'], 'count': agg_result['count']})
            return agg_result

        tool = Tool(function_declarations=[
            FunctionDeclaration.from_func(get_models),
            FunctionDeclaration.from_func(get_schema),
            FunctionDeclaration.from_func(search_odoo),
            FunctionDeclaration.from_func(search_odoo_aggregate),
        ])
        model = GenerativeModel(VERTEX_DEFAULT_MODEL, tools=[tool])
        responder = AutomaticFunctionCallingResponder(max_automatic_function_calls=VERTEX_MAX_FUNCTION_CALLS)
        chat = model.start_chat(responder=responder)

        try:
            response = chat.send_message(query_text)
        except Exception as e:
            _logger.exception("Vertex AI request failed: %s", str(e))
            raise UserError(_("Vertex AI service error: %s") % str(e))

        last = last_result[-1] if last_result else None
        return {
            'provider': 'vertex_ai',
            'answer': response.text,
            'multi_model': False,
            'model': last['model_name'] if last else None,
            'records': last['records'] if last else [],
            'count': last['count'] if last else 0,
            'fields': last['fields'] if last else [],
        }

    def _extract_json_from_ai_response(self, content):
        """
        Extract JSON from AI response text, handling various formats the AI might return.
        
        Args:
            content (str): The raw text response from the AI
            
        Returns:
            dict: Parsed JSON data
            
        Raises:
            UserError: If JSON cannot be extracted or parsed
        """
        try:
            # First try direct JSON parsing (in case it returns clean JSON)
            return json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON from within markdown code blocks if present
            json_block_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', content)
            if json_block_match:
                try:
                    return json.loads(json_block_match.group(1).strip())
                except json.JSONDecodeError:
                    # If that fails, fall back to the generic JSON object extraction
                    json_match = re.search(r'\{[\s\S]*?\}', content, re.DOTALL)
                    if json_match:
                        try:
                            return json.loads(json_match.group(0))
                        except json.JSONDecodeError as e:
                            _logger.error("Failed to parse extracted JSON: %s for content: %s", str(e), json_match.group(0))
                            raise UserError(_("Could not parse AI response as JSON. Please try again."))
                    else:
                        raise UserError(_("AI response is not in the expected JSON format. Please try again."))
            else:
                # If no code block, try the generic JSON object extraction
                json_match = re.search(r'\{[\s\S]*?\}', content, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except json.JSONDecodeError as e:
                        _logger.error("Failed to parse extracted JSON: %s for content: %s", str(e), json_match.group(0))
                        raise UserError(_("Could not parse AI response as JSON. Please try again."))
                else:
                    raise UserError(_("AI response is not in the expected JSON format. Please try again."))
    
    def execute_query(self, query_data):
        """Safely execute the generated ORM query"""
        # Check if this is a multi-model query
        if query_data.get('multi_model'):
            return self._execute_multi_model_query(query_data)
        
        # Check if this is an aggregation query
        if query_data.get('aggregation'):
            return self._execute_aggregation_query(query_data)
        
        # Handle single model query
        model_name = query_data.get('model')
        domain = query_data.get('domain', [])
        fields = query_data.get('fields', [])
        limit = query_data.get('limit', 80)

        try:
            search_result = self._execute_search(model_name, domain, fields, limit)
            return {
                'multi_model': False,
                'model': model_name,
                'records': search_result['records'],
                'count': search_result['count'],
                'fields': search_result['fields'],
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Query execution error: %s", str(e))
            raise UserError(_("Error executing query: %s") % str(e))

    def _execute_search(self, model_name, domain, fields=None, limit=None, allowlist=None):
        """Shared security-hardened ORM search. Runs through self.env (bound to the
        calling user via request.env, never sudo()). Used by both the OpenRouter and
        Vertex AI query paths.
        """
        if allowlist is not None and model_name not in allowlist:
            raise UserError(_("Model '%s' is not in the allowed list.") % model_name)
        if not model_name or not self.env['ir.model'].search([('model', '=', model_name)]):
            raise UserError(_("Invalid model: %s") % model_name)
        if not isinstance(domain, list) or not all(
            isinstance(d, (list, tuple)) and len(d) == 3 for d in domain
        ):
            raise UserError(_("Invalid search domain."))
        limit = min(int(limit), HARD_SEARCH_LIMIT) if limit else HARD_SEARCH_LIMIT
        model = self.env[model_name]
        records = model.search(domain, limit=limit)
        available_fields = list(model.fields_get().keys())
        if fields:
            valid_fields = [f for f in fields if f in available_fields]
            if not valid_fields:
                if 'display_name' in available_fields:
                    valid_fields = ['display_name']
                elif 'name' in available_fields:
                    valid_fields = ['name']
                elif 'id' in available_fields:
                    valid_fields = ['id']
                else:
                    valid_fields = [available_fields[0]] if available_fields else ['id']
            fields = valid_fields
        else:
            fields = ['display_name']
        result = records.read(fields)
        return {'records': result, 'fields': fields, 'count': len(result)}

    def _execute_multi_model_query(self, query_data):
        """Execute queries on multiple models and return combined results"""
        queries = query_data.get('queries', [])
        if not queries:
            raise UserError(_("No valid queries provided for multi-model search"))
        
        results = []
        total_count = 0
        
        # First pass: collect all primary records
        query_results = {}
        for idx, query in enumerate(queries):
            model_name = query.get('model')
            domain = query.get('domain', [])
            fields = query.get('fields', [])
            limit = query.get('limit', 20)  # Lower default limit for multi-model queries
            
            # Validate model exists and is accessible
            if not model_name or not self.env['ir.model'].search([('model', '=', model_name)]):
                _logger.warning("Invalid model in multi-query: %s", model_name)
                continue
            
            try:
                # Execute query using ORM
                model = self.env[model_name]
                records = model.search(domain, limit=limit)
                
                # Get available fields for this model
                available_fields = list(model.fields_get().keys())
                
                # Validate and filter fields to only include ones that exist in the model
                if fields:
                    valid_fields = [field for field in fields if field in available_fields]
                    
                    # If no valid fields remain after filtering, use defaults
                    if not valid_fields:
                        _logger.warning("No valid fields found in AI suggestion for model %s. Using defaults.", model_name)
                        if 'display_name' in available_fields:
                            valid_fields = ['display_name']
                        elif 'name' in available_fields:
                            valid_fields = ['name']
                        elif 'id' in available_fields:
                            valid_fields = ['id']
                        else:
                            valid_fields = [available_fields[0]] if available_fields else ['id']
                    
                    fields = valid_fields
                else:
                    fields = ['display_name']
                
                model_result = records.read(fields)
                
                # Store the results and model info for potential joining in second pass
                query_results[idx] = {
                    'model_name': model_name,
                    'model': model,
                    'records': model_result,
                    'record_ids': records.ids,
                    'fields': fields
                }
            except Exception as e:
                _logger.error("Query execution error for model %s: %s", model_name, str(e))
                # Continue with other queries even if one fails
        
        # Process the results (with basic joining logic for common scenarios)
        for idx, query_result in query_results.items():
            model_name = query_result['model_name']
            model_result = query_result['records']
            fields = query_result['fields']
            
            # Get human-readable model name
            model_info = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
            model_label = model_info.name if model_info else model_name
            
            # Add to the final results
            results.append({
                'model': model_name,
                'model_label': model_label,
                'records': model_result,
                'count': len(model_result),
                'fields': fields
            })
            
            total_count += len(model_result)
            
        # Get model relationship information from ir.model.fields
        model_relationships = self._discover_model_relationships(list(query_results.keys()), query_results)
        
        # Process the model relationships and join related data
        if model_relationships:
            # Some relationships were found, let's join the data
            _logger.info("Found %d potential model relationships to process", len(model_relationships))
            
            for relation in model_relationships:
                source_idx = relation['source_idx']
                target_idx = relation['target_idx']
                field_name = relation['field_name']
                relation_type = relation['relation_type']
                
                source_result = query_results.get(source_idx)
                target_result = query_results.get(target_idx)
                
                if not source_result or not target_result:
                    continue
                
                # Create lookup dictionaries for efficient joining
                if relation_type == 'many2one':
                    # Many2one: source records point to target records
                    target_dict = {rec['id']: rec for rec in target_result['records']}
                    
                    # For each source record, add the related target record info
                    for source_rec in source_result['records']:
                        relation_id = source_rec.get(field_name) 
                        
                        # Many2one fields are usually tuples [id, display_name] or just the ID
                        if isinstance(relation_id, (list, tuple)) and len(relation_id) > 0:
                            relation_id = relation_id[0]
                            
                        if relation_id and relation_id in target_dict:
                            # Add the related info using a consistent naming pattern
                            related_info_key = f"{target_result['model_name'].replace('.', '_')}_info"
                            source_rec[related_info_key] = target_dict[relation_id]
                            
                            # Mark this record as having linked data
                            source_rec['has_linked_data'] = True
                
                # Update the results metadata for any model that got enhanced
                for result in results:
                    if result['model'] == source_result['model_name']:
                        result['has_linked_data'] = True
                        result['linked_model'] = target_result['model_name']
        
        # Final result structure
        final_result = {
            'multi_model': True,
            'results': results,
            'total_count': total_count
        }
        
        # Add debug logging to trace the structure
        _logger.info(
            "Multi-model query complete: %d models, %d total records, structure valid: %s", 
            len(results), 
            total_count,
            bool(results and isinstance(results, list))
        )
        
        # Additional validation before return
        if not results or not isinstance(results, list) or total_count == 0:
            _logger.warning(
                "Potential issue with multi-model results: models=%d, records=%d", 
                len(results) if results else 0, 
                total_count
            )
        
        # Pre-process data to ensure it's JSON serializable
        def make_serializable(item):
            if isinstance(item, dict):
                return {k: make_serializable(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [make_serializable(i) for i in item]
            elif hasattr(item, 'isoformat'): # Handle date/datetime
                return item.isoformat()
            else:
                return item
                
        # Apply serialization pre-processing to the result structure
        try:
            processed_results = []
            for model_result in results:
                processed_records = []
                for record in model_result.get('records', []):
                    processed_record = {}
                    for field, value in record.items():
                        processed_record[field] = make_serializable(value)
                    processed_records.append(processed_record)
                
                model_result_copy = dict(model_result)
                model_result_copy['records'] = processed_records
                processed_results.append(model_result_copy)
                
            final_result['results'] = processed_results
        except Exception as e:
            _logger.error("Error pre-processing results for serialization: %s", str(e))
            # Continue with original results if there's an error
        
        return final_result


    def _execute_aggregation_query(self, query_data):
        """
        Execute an aggregation query using Odoo's read_group method
        This handles GROUP BY operations and returns properly formatted data for visualization
        """
        model_name = query_data.get('model')
        domain = query_data.get('domain', [])
        group_by = query_data.get('group_by', [])
        measures = query_data.get('measures', ['__count'])
        limit = query_data.get('limit', 100)
        
        _logger.info("Starting aggregation query execution with data: %s", query_data)
        
        if not model_name:
            _logger.error("Aggregation query missing model name")
            raise UserError(_("Model name is required for aggregation queries"))
            
        if not group_by:
            _logger.error("Aggregation query missing group_by fields")
            raise UserError(_("Group by fields are required for aggregation queries"))
        
        # Get model information before trying to access it
        model_exists = self.env['ir.model'].search_count([('model', '=', model_name)])
        if not model_exists:
            _logger.error("Invalid model for aggregation: %s", model_name)
            raise UserError(_("Invalid model: %s") % model_name)
        
        # Special handling for login aggregation
        if model_name == 'res.users.log':
            _logger.info("Detected aggregation on res.users.log - ensuring create_date field is available")
            # Make sure create_date is handled specially for log models
            if any('create_date' in gb for gb in group_by):
                _logger.info("Group by includes create_date field")
        
        try:
            # Execute aggregation query using read_group
            model = self.env[model_name]
            
            # Get human-readable model name
            model_info = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
            model_label = model_info.name if model_info else model_name
            
            # Validate that the group by fields exist in the model
            fields_info = model.fields_get()
            available_fields = list(fields_info.keys())
            _logger.info("Available fields in %s: %s", model_name, available_fields)
            
            # Validate and filter measures to only include fields that exist in the model
            valid_measures = []
            for measure in measures:
                if measure == '__count':
                    valid_measures.append(measure)  # Special case for count
                elif measure in available_fields:
                    valid_measures.append(measure)
                else:
                    _logger.warning("Measure field '%s' does not exist in model %s, skipping", measure, model_name)
            
            # If all measures were invalid, default to __count
            if not valid_measures:
                _logger.warning("No valid measures found, defaulting to __count")
                valid_measures = ['__count']
                
            # Replace original measures with validated list
            measures = valid_measures
            
            # Map common field name patterns to actual field names if needed
            field_mapping = {}
            
            # Auto-detect date fields for account.move if the standard mapping isn't working
            if model_name == 'account.move':
                date_fields = [field for field in available_fields if 'date' in field.lower()]
                _logger.info("Found date fields in %s: %s", model_name, date_fields)
                
                # Create mappings for common date field names
                if 'date' in group_by[0] and 'date' not in available_fields:
                    if 'invoice_date' in available_fields:
                        field_mapping['date'] = 'invoice_date'
                    elif 'accounting_date' in available_fields:
                        field_mapping['date'] = 'accounting_date'
                    elif len(date_fields) > 0:
                        field_mapping['date'] = date_fields[0]
                
            # Process each group_by field
            corrected_group_by = []
            for gb in group_by:
                # Extract the field name without the granularity part
                field_parts = gb.split(':')
                field_name = field_parts[0]
                granularity = field_parts[1] if len(field_parts) > 1 else None
                
                # Check if we need to map the field name
                if field_name in field_mapping:
                    original_field = field_name
                    field_name = field_mapping[field_name]
                    _logger.info("Mapped field '%s' to actual field '%s'", original_field, field_name)
                
                # Validate the field exists
                if field_name not in available_fields:
                    # Try to find a similar field as a fallback
                    similar_fields = [f for f in available_fields if field_name.lower() in f.lower()]
                    if similar_fields:
                        field_name = similar_fields[0]
                        _logger.info("Field '%s' not found, using similar field '%s' instead", 
                                    field_parts[0], field_name)
                    else:
                        _logger.error("Group by field '%s' does not exist in model %s", field_name, model_name)
                        raise UserError(_("Field '%s' does not exist in model %s") % (field_name, model_name))
                
                # Reconstruct the group_by expression
                if granularity:
                    corrected_group_by.append(f"{field_name}:{granularity}")
                else:
                    corrected_group_by.append(field_name)
            
            # Replace the original group_by with our corrected version
            if corrected_group_by != group_by:
                _logger.info("Corrected group_by from %s to %s", group_by, corrected_group_by)
                group_by = corrected_group_by
            
            # Execute the aggregation
            _logger.info("Executing aggregation query: model=%s, domain=%s, group_by=%s, measures=%s", 
                        model_name, domain, group_by, measures)
            
            # Handle measures - if only __count is requested, pass empty list
            # This is because Odoo's read_group automatically counts records when fields is empty
            orm_measures = []
            
            # Only include non-count measures
            for measure in measures:
                if measure != '__count':
                    orm_measures.append(measure)
            
            # Execute the query with read_group
            result = model.read_group(
                domain=domain,
                fields=orm_measures,  # Empty list or non-count measures only
                groupby=group_by,
                limit=limit,
                orderby=f"{group_by[0]} ASC" if group_by else False,  # Sort by the first groupby field
                lazy=False  # Ensure all groups are returned even if empty
            )
            
            _logger.info("Aggregation query returned %d results", len(result))
            if result:
                _logger.info("First result row: %s", result[0])

            # Format results for visualization - converting to dimension/measure format
            records = []
            fields = []
            
            # Determine the dimension (group by) and measure fields
            # Store both the base field name and the full field name with granularity
            full_dimension_field = group_by[0] if group_by else None
            dimension_field = full_dimension_field.split(':')[0] if full_dimension_field else None
            measure_field = measures[0] if measures else '__count'
            display_measure = measure_field if measure_field != '__count' else 'count'
            
            # Add fields metadata
            fields = [dimension_field, display_measure]
            
            # Get field descriptions for more readable labels
            field_descriptions = {}
            if dimension_field:
                field_info = model.fields_get([dimension_field])
                if dimension_field in field_info:
                    field_descriptions[dimension_field] = field_info[dimension_field]['string']
            
            # Process each result row
            for row in result:
                record = {}
                
                # Handle the dimension (group by) value
                if dimension_field:
                    # The key in result will contain the granularity suffix if present
                    # Try the full field name first, then fall back to base field name
                    key_to_use = full_dimension_field if full_dimension_field in row else dimension_field
                    
                    # Extract the value and label for the dimension field
                    dimension_value = row.get(key_to_use)
                    
                    # For many2one fields, the value is a tuple (id, name)
                    if isinstance(dimension_value, tuple) and len(dimension_value) == 2:
                        record[dimension_field] = dimension_value[1]  # Use name for display
                    else:
                        record[dimension_field] = dimension_value
                
                # Handle the measure (count/sum) value
                if measure_field == '__count':
                    record[display_measure] = row.get('__count', 0)
                else:
                    record[display_measure] = row.get(measure_field, 0)
                
                records.append(record)
            
            # Return in a format compatible with the visualization component
            return {
                'aggregation': True,
                'model': model_name,
                'model_label': model_label,
                'dimension': dimension_field,
                'measure': display_measure,
                'records': records,
                'count': len(records),
                'fields': fields,
                'field_descriptions': field_descriptions
            }
            
        except Exception as e:
            _logger.error("Query execution error: %s", str(e), exc_info=True)
            raise UserError(_("Error executing aggregation query: %s") % str(e))
    
    def _discover_model_relationships(self, query_indexes, query_results):
        """
        Dynamically discover relationships between models in the query results.
        
        Args:
            query_indexes: List of query result indexes
            query_results: Dictionary of query results by index
            
        Returns:
            List of relationship dictionaries with info on how to join the data
        """
        if not query_indexes or len(query_indexes) < 2:
            return []
            
        relationships = []
        
        # Get all the models involved in the query
        models_in_query = {idx: res['model_name'] for idx, res in query_results.items() if res}
        
        # For each pair of models, check if there's a relation between them
        for source_idx in query_indexes:
            source_model = models_in_query.get(source_idx)
            if not source_model:
                continue
                
            # Get field definitions for this model to find relationships
            model_fields = self.env['ir.model.fields'].search([
                ('model', '=', source_model),
                ('ttype', 'in', ['many2one', 'one2many', 'many2many']),
            ])
            
            # Check each field to see if it relates to another model in our query
            for field in model_fields:
                relation_model = field.relation
                
                # Skip if there's no relation or if it points to a model not in our query
                if not relation_model:
                    continue
                    
                # Find the target model index in our query results
                target_idx = None
                for idx, model_name in models_in_query.items():
                    if model_name == relation_model:
                        target_idx = idx
                        break
                        
                if target_idx is None:
                    continue  # No matching model in our results
                    
                # We found a relation, build the relationship info
                relationship = {
                    'source_idx': source_idx,
                    'target_idx': target_idx,
                    'field_name': field.name,
                    'relation_type': field.ttype,
                    'source_model': source_model,
                    'target_model': relation_model,
                }
                
                relationships.append(relationship)
                _logger.info(
                    "Found relationship: %s.%s (%s) -> %s", 
                    source_model, field.name, field.ttype, relation_model
                )
        
        return relationships


class AISearchSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    openrouter_api_key = fields.Char(string="OpenRouter API Key")
    ai_provider = fields.Selection([
        ('openrouter', 'OpenRouter'),
        ('vertex_ai', 'Google Vertex AI'),
    ], string="AI Provider", default='openrouter', required=True)
    vertex_project_id = fields.Char(string="Vertex AI Project ID")
    vertex_region = fields.Char(string="Vertex AI Region", default='europe-west4')
    vertex_allowed_models = fields.Char(
        string="Vertex AI Allowed Models",
        help="Comma-separated list of technical Odoo model names the AI is allowed to query, "
             "e.g. sale.order,res.partner,product.product. Empty means no models are allowed."
    )

    def get_values(self):
        res = super(AISearchSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            openrouter_api_key=params.get_param('leulit_ai.openrouter_api_key', ''),
            ai_provider=params.get_param('leulit_ai.ai_provider', 'openrouter'),
            vertex_project_id=params.get_param('leulit_ai.vertex_project_id', ''),
            vertex_region=params.get_param('leulit_ai.vertex_region', 'europe-west4'),
            vertex_allowed_models=params.get_param('leulit_ai.vertex_allowed_models', ''),
        )
        return res

    def set_values(self):
        super(AISearchSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('leulit_ai.openrouter_api_key', self.openrouter_api_key or '')
        params.set_param('leulit_ai.ai_provider', self.ai_provider or 'openrouter')
        params.set_param('leulit_ai.vertex_project_id', self.vertex_project_id or '')
        params.set_param('leulit_ai.vertex_region', self.vertex_region or 'europe-west4')
        params.set_param('leulit_ai.vertex_allowed_models', self.vertex_allowed_models or '')
